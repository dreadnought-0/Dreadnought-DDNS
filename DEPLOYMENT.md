# Deployment Guide

This guide covers production deployment options for the DDNS Manager.

## Docker Compose (Recommended)

The simplest production deployment uses Docker Compose with a reverse proxy.

### 1. Prepare Environment

```bash
# Create directory
mkdir -p /opt/ddns-manager
cd /opt/ddns-manager

# Clone or copy files
git clone <repository-url> .

# Create environment file
cp .env.sample .env
```

### 2. Configure Environment

Edit `.env` with production values:

```env
# Cloudflare API Token - REQUIRED
CF_API_TOKEN=your_production_token

# Admin credentials - CHANGE THESE
ADMIN_EMAIL=admin@yourdomain.com
ADMIN_PASSWORD=StrongPasswordHere

# Generate a strong secret key (use openssl rand -hex 32)
SECRET_KEY=your-generated-secret-key

# Production settings
POLL_INTERVAL_SECONDS=300
IPV6_ENABLED=true

# Optional notifications
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

### 3. Start Services

```bash
docker compose up -d
```

### 4. Configure Reverse Proxy

#### Nginx Example

```nginx
server {
    listen 80;
    server_name ddns.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name ddns.yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8081;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### Traefik Example

```yaml
# docker-compose.override.yml
version: '3.8'

services:
  web:
    labels:
      - traefik.enable=true
      - traefik.http.routers.ddns-web.rule=Host(`ddns.yourdomain.com`)
      - traefik.http.routers.ddns-web.tls=true
      - traefik.http.routers.ddns-web.tls.certresolver=letsencrypt
      - traefik.http.services.ddns-web.loadbalancer.server.port=3000

  api:
    labels:
      - traefik.enable=true
      - traefik.http.routers.ddns-api.rule=Host(`ddns.yourdomain.com`) && PathPrefix(`/api`)
      - traefik.http.routers.ddns-api.tls=true
      - traefik.http.routers.ddns-api.tls.certresolver=letsencrypt
      - traefik.http.services.ddns-api.loadbalancer.server.port=8000

networks:
  default:
    external:
      name: traefik
```

## Systemd Service

For non-Docker deployments, create systemd services:

### 1. Install Dependencies

```bash
# Python 3.12
sudo apt update
sudo apt install python3.12 python3.12-venv python3-pip

# Node.js 18+
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install nodejs

# SQLite
sudo apt install sqlite3
```

### 2. Setup Application

```bash
# Create user
sudo useradd -r -s /bin/false -d /opt/ddns-manager ddns-manager

# Create directories
sudo mkdir -p /opt/ddns-manager/{backend,frontend}
sudo mkdir -p /var/lib/ddns-manager
sudo chown ddns-manager:ddns-manager /var/lib/ddns-manager

# Install backend
cd /opt/ddns-manager/backend
sudo -u ddns-manager python3.12 -m venv venv
sudo -u ddns-manager ./venv/bin/pip install -r requirements.txt

# Build frontend
cd /opt/ddns-manager/frontend
sudo -u ddns-manager npm install
sudo -u ddns-manager npm run build
```

### 3. Create Systemd Services

#### API Service

```ini
# /etc/systemd/system/ddns-api.service
[Unit]
Description=DDNS Manager API
After=network.target
Requires=network.target

[Service]
Type=exec
User=ddns-manager
Group=ddns-manager
WorkingDirectory=/opt/ddns-manager/backend
Environment=DATABASE_URL=sqlite:///var/lib/ddns-manager/ddns.db
EnvironmentFile=/etc/ddns-manager.env
ExecStart=/opt/ddns-manager/backend/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### Worker Service

```ini
# /etc/systemd/system/ddns-worker.service
[Unit]
Description=DDNS Manager Worker
After=network.target
Requires=network.target

[Service]
Type=exec
User=ddns-manager
Group=ddns-manager
WorkingDirectory=/opt/ddns-manager/backend
Environment=DATABASE_URL=sqlite:///var/lib/ddns-manager/ddns.db
EnvironmentFile=/etc/ddns-manager.env
ExecStart=/opt/ddns-manager/backend/venv/bin/python worker.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### Frontend Service (with Node.js)

```ini
# /etc/systemd/system/ddns-web.service
[Unit]
Description=DDNS Manager Web
After=network.target
Requires=network.target

[Service]
Type=exec
User=ddns-manager
Group=ddns-manager
WorkingDirectory=/opt/ddns-manager/frontend
Environment=NODE_ENV=production
Environment=NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
ExecStart=/usr/bin/node server.js
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 4. Environment Configuration

```bash
# /etc/ddns-manager.env
CF_API_TOKEN=your_token
ADMIN_EMAIL=admin@yourdomain.com
ADMIN_PASSWORD=secure_password
SECRET_KEY=generated_secret_key
POLL_INTERVAL_SECONDS=300
IPV6_ENABLED=true
```

### 5. Enable and Start Services

```bash
sudo systemctl enable ddns-api ddns-worker ddns-web
sudo systemctl start ddns-api ddns-worker ddns-web
sudo systemctl status ddns-api ddns-worker ddns-web
```

## Security Hardening

### 1. Firewall Configuration

```bash
# Allow only necessary ports
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 2. SSL/TLS Certificate

Use Let's Encrypt with Certbot:

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d ddns.yourdomain.com
```

### 3. Database Security

```bash
# Set proper permissions
sudo chmod 640 /var/lib/ddns-manager/ddns.db
sudo chown ddns-manager:ddns-manager /var/lib/ddns-manager/ddns.db
```

### 4. Log Configuration

```bash
# Configure log rotation
sudo tee /etc/logrotate.d/ddns-manager << EOF
/var/log/ddns-manager/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 ddns-manager ddns-manager
    postrotate
        systemctl reload ddns-api ddns-worker ddns-web
    endscript
}
EOF
```

## Monitoring

### 1. Health Checks

Add monitoring for service health:

```bash
#!/bin/bash
# /opt/ddns-manager/healthcheck.sh

# Check API health
if ! curl -f http://127.0.0.1:8081/health >/dev/null 2>&1; then
    echo "API health check failed"
    exit 1
fi

# Check web health  
if ! curl -f http://127.0.0.1:8080/health >/dev/null 2>&1; then
    echo "Web health check failed"
    exit 1
fi

echo "All services healthy"
```

### 2. Log Monitoring

Monitor logs for errors:

```bash
# Check for API errors
sudo journalctl -u ddns-api -f --grep ERROR

# Check for worker errors
sudo journalctl -u ddns-worker -f --grep ERROR
```

### 3. Metrics Collection

Consider integrating with monitoring systems like:
- Prometheus + Grafana
- DataDog
- New Relic

## Backup Strategy

### 1. Database Backup

```bash
#!/bin/bash
# /opt/ddns-manager/backup.sh

BACKUP_DIR="/var/backups/ddns-manager"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

# Backup database
cp /var/lib/ddns-manager/ddns.db "$BACKUP_DIR/ddns_$DATE.db"

# Compress old backups
find "$BACKUP_DIR" -name "ddns_*.db" -mtime +7 -exec gzip {} \;

# Remove old backups
find "$BACKUP_DIR" -name "ddns_*.db.gz" -mtime +30 -delete
```

Add to crontab:
```bash
0 2 * * * /opt/ddns-manager/backup.sh
```

### 2. Configuration Backup

```bash
# Backup configuration
tar -czf /var/backups/ddns-config-$(date +%Y%m%d).tar.gz \
    /opt/ddns-manager \
    /etc/ddns-manager.env \
    /etc/systemd/system/ddns-*.service
```

## Updates

### Docker Compose Updates

```bash
cd /opt/ddns-manager

# Pull new images
docker compose pull

# Restart services
docker compose up -d

# Clean up old images
docker system prune -af
```

### Manual Updates

```bash
# Backup first
sudo systemctl stop ddns-api ddns-worker ddns-web

# Update code
git pull origin main

# Update backend dependencies
cd /opt/ddns-manager/backend
sudo -u ddns-manager ./venv/bin/pip install -r requirements.txt

# Update frontend
cd /opt/ddns-manager/frontend
sudo -u ddns-manager npm install
sudo -u ddns-manager npm run build

# Restart services
sudo systemctl start ddns-api ddns-worker ddns-web
```

## Troubleshooting

### Common Issues

1. **Service won't start**: Check logs with `journalctl -u service-name -n 50`
2. **Database locked**: Ensure only one process accesses SQLite
3. **API token invalid**: Verify token permissions and expiration
4. **Rate limiting**: Increase poll interval or check for competing applications

### Debug Commands

```bash
# Check service status
sudo systemctl status ddns-api ddns-worker ddns-web

# View logs
sudo journalctl -u ddns-api -f
sudo journalctl -u ddns-worker -f  
sudo journalctl -u ddns-web -f

# Test API directly
curl -v http://127.0.0.1:8081/health

# Check database
sqlite3 /var/lib/ddns-manager/ddns.db ".tables"
```

This deployment guide provides production-ready configurations for running the DDNS Manager securely and reliably.