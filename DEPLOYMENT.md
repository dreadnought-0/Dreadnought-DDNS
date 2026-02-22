# Deployment Guide

This guide covers production deployment options for Dreadnought DDNS Manager.

---

## Option 1 — Coolify (Recommended)

[Coolify](https://coolify.io) is a self-hosted PaaS that handles TLS, reverse proxying, and Docker orchestration automatically. It is the easiest way to run Dreadnought on a VPS.

### Steps

1. In Coolify, create a new **Docker Compose** resource pointing to `https://github.com/dreadnought-0/Dreadnought-DDNS`
2. Set all environment variables in the Coolify UI (see table in README)
3. Assign a public domain to the **`web`** service (e.g. `ddns.yourdomain.com`)
4. Assign a public domain to the **`api`** service (e.g. `ddns-api.yourdomain.com`)
5. Set the `NEXT_PUBLIC_API_URL` environment variable on the **`web`** service to the full public URL of the API:
   ```
   NEXT_PUBLIC_API_URL=https://ddns-api.yourdomain.com
   ```
6. The **`worker`** service runs in the background — no domain needed
7. Deploy

> Coolify manages the data directory, file permissions, and TLS certificates automatically. You do not need to run `setup.sh`.

### Why `NEXT_PUBLIC_API_URL` matters

This variable is baked into the frontend JavaScript at build time. It tells the browser where to send API calls. If it is left as `http://localhost:8081` (the docker-compose default), API calls will fail for anyone visiting your site from outside the host machine. Always set it to the public URL of your `api` service when deploying remotely.

---

## Option 2 — Docker Compose on a Linux Host / Raspberry Pi

Use this method if you are running directly on a VPS, home server, or Raspberry Pi without a PaaS layer.

### 1. Clone and Configure

```bash
git clone https://github.com/dreadnought-0/Dreadnought-DDNS.git
cd Dreadnought-DDNS

cp .env.sample .env
nano .env   # Fill in your values
```

### 2. Prepare the Data Directory

The SQLite database is stored in `./data`. Docker needs write access to it before the containers start. This step is **only required for bare-metal deployments** — Coolify and similar platforms handle it automatically.

```bash
mkdir -p ./data
chmod 777 ./data
```

Alternatively, run the included helper script which does the same thing and validates your `.env`:

```bash
chmod +x setup.sh && ./setup.sh
```

### 3. Update `NEXT_PUBLIC_API_URL`

If you are exposing this behind a reverse proxy with a real domain, edit `docker-compose.yml` and update the `web` service's environment:

```yaml
web:
  environment:
    - NEXT_PUBLIC_API_URL=https://ddns-api.yourdomain.com
```

If you are only accessing the app locally (e.g. on your LAN), you can leave it as `http://localhost:8081`.

### 4. Start Services

```bash
docker compose up -d

# Verify all three containers are running and healthy
docker compose ps

# Follow logs
docker compose logs -f
```

Default local ports:
- **Web UI**: http://localhost:8082
- **API**: http://localhost:8081

### 5. Reverse Proxy (for public HTTPS access)

Pick one of the following to put in front of the app.

#### Nginx

```nginx
server {
    listen 80;
    server_name ddns.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name ddns.yourdomain.com;

    ssl_certificate     /etc/letsencrypt/live/ddns.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ddns.yourdomain.com/privkey.pem;

    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;

    # Frontend
    location / {
        proxy_pass http://127.0.0.1:8082;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Separate subdomain for the API
server {
    listen 443 ssl http2;
    server_name ddns-api.yourdomain.com;

    ssl_certificate     /etc/letsencrypt/live/ddns-api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ddns-api.yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8081;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Get certificates with Certbot:
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d ddns.yourdomain.com -d ddns-api.yourdomain.com
```

#### Traefik (docker-compose.override.yml)

If you already have Traefik running as a Docker network proxy, create a `docker-compose.override.yml` alongside the main file:

```yaml
services:
  web:
    environment:
      - NEXT_PUBLIC_API_URL=https://ddns-api.yourdomain.com
    labels:
      - traefik.enable=true
      - traefik.http.routers.ddns-web.rule=Host(`ddns.yourdomain.com`)
      - traefik.http.routers.ddns-web.tls=true
      - traefik.http.routers.ddns-web.tls.certresolver=letsencrypt
      - traefik.http.services.ddns-web.loadbalancer.server.port=3000

  api:
    labels:
      - traefik.enable=true
      - traefik.http.routers.ddns-api.rule=Host(`ddns-api.yourdomain.com`)
      - traefik.http.routers.ddns-api.tls=true
      - traefik.http.routers.ddns-api.tls.certresolver=letsencrypt
      - traefik.http.services.ddns-api.loadbalancer.server.port=8000

networks:
  default:
    external:
      name: traefik
```

---

## Option 3 — Systemd (no Docker)

Use this only if Docker is not available on your system.

### 1. Install Dependencies

```bash
sudo apt update
sudo apt install python3.12 python3.12-venv python3-pip nodejs npm sqlite3
```

### 2. Create Application User and Directories

```bash
sudo useradd -r -s /bin/false -d /opt/dreadnought dreadnought
sudo mkdir -p /opt/dreadnought/{backend,frontend}
sudo mkdir -p /var/lib/dreadnought
sudo chown dreadnought:dreadnought /var/lib/dreadnought
```

### 3. Install and Build

```bash
# Backend
cd /opt/dreadnought/backend
sudo -u dreadnought python3.12 -m venv venv
sudo -u dreadnought ./venv/bin/pip install -r requirements.txt

# Frontend
cd /opt/dreadnought/frontend
sudo -u dreadnought npm install
sudo -u dreadnought npm run build
```

### 4. Environment File

```bash
# /etc/dreadnought.env
CF_API_TOKEN=your_token
ADMIN_EMAIL=admin@yourdomain.com
ADMIN_PASSWORD=secure_password
SECRET_KEY=generated_secret_key
POLL_INTERVAL_SECONDS=300
IPV6_ENABLED=false
DATABASE_URL=sqlite:////var/lib/dreadnought/ddns.db
```

### 5. Systemd Service Files

**API** (`/etc/systemd/system/dreadnought-api.service`):
```ini
[Unit]
Description=Dreadnought DDNS API
After=network.target

[Service]
Type=exec
User=dreadnought
WorkingDirectory=/opt/dreadnought/backend
EnvironmentFile=/etc/dreadnought.env
ExecStart=/opt/dreadnought/backend/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Worker** (`/etc/systemd/system/dreadnought-worker.service`):
```ini
[Unit]
Description=Dreadnought DDNS Worker
After=network.target

[Service]
Type=exec
User=dreadnought
WorkingDirectory=/opt/dreadnought/backend
EnvironmentFile=/etc/dreadnought.env
ExecStart=/opt/dreadnought/backend/venv/bin/python worker.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Frontend** (`/etc/systemd/system/dreadnought-web.service`):
```ini
[Unit]
Description=Dreadnought DDNS Frontend
After=network.target

[Service]
Type=exec
User=dreadnought
WorkingDirectory=/opt/dreadnought/frontend
Environment=NODE_ENV=production
Environment=NEXT_PUBLIC_API_URL=https://ddns-api.yourdomain.com
ExecStart=/usr/bin/node .next/standalone/server.js
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 6. Enable and Start

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now dreadnought-api dreadnought-worker dreadnought-web
sudo systemctl status dreadnought-api dreadnought-worker dreadnought-web
```

---

## Updating

### Docker Compose

```bash
cd /path/to/Dreadnought-DDNS

git pull origin main

# Rebuild images and restart (data is preserved in ./data)
docker compose up -d --build

# Clean up old build layers
docker system prune -f
```

### Systemd

```bash
sudo systemctl stop dreadnought-api dreadnought-worker dreadnought-web

git pull origin main

cd /opt/dreadnought/backend
sudo -u dreadnought ./venv/bin/pip install -r requirements.txt

cd /opt/dreadnought/frontend
sudo -u dreadnought npm install && sudo -u dreadnought npm run build

sudo systemctl start dreadnought-api dreadnought-worker dreadnought-web
```

---

## Security Hardening

### Firewall (bare-metal Linux)

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

Block direct access to app ports so all traffic must go through the reverse proxy:

```bash
sudo ufw deny 8081/tcp
sudo ufw deny 8082/tcp
```

### Secrets

- Use `openssl rand -hex 32` to generate `SECRET_KEY`
- Never commit `.env` to version control
- Rotate your Cloudflare API token periodically
- Scope the token to only the zones Dreadnought needs to manage

---

## Backup

The entire application state lives in a single SQLite file.

```bash
# Docker Compose
cp ./data/ddns.db ./backups/ddns_$(date +%Y%m%d_%H%M%S).db

# Systemd
cp /var/lib/dreadnought/ddns.db /var/backups/ddns_$(date +%Y%m%d_%H%M%S).db
```

A simple daily cron entry:

```bash
0 2 * * * cp /path/to/data/ddns.db /path/to/backups/ddns_$(date +\%Y\%m\%d).db
```

---

## Troubleshooting

### Docker Compose

```bash
# Check container status
docker compose ps

# Tail logs for a specific service
docker compose logs -f api
docker compose logs -f worker
docker compose logs -f web

# Restart a single service
docker compose restart api

# Full rebuild
docker compose down && docker compose up -d --build
```

### Systemd

```bash
sudo systemctl status dreadnought-api
sudo journalctl -u dreadnought-api -f
sudo journalctl -u dreadnought-worker -f
```

### Common Errors

| Error | Fix |
|---|---|
| `unable to open database file` | `mkdir -p ./data && chmod 777 ./data` |
| API calls failing in browser | Check `NEXT_PUBLIC_API_URL` is set to the public API domain |
| `Failed to resolve zone_id` | Verify API token has `Zone → Zone → Read` permission |
| Container stuck "unhealthy" | Check logs — usually a missing env var or permission issue |
| `CNAME record exists` | Remove the conflicting CNAME from Cloudflare first |