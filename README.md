# Dreadnought DDNS Manager

A production-ready, self-hosted Dynamic DNS (DDNS) manager for Cloudflare that automatically updates your DNS A/AAAA records whenever your public IP address changes.

**[Live Demo](http://ddns.demo.dreadnought.work/)** — Use `me@example.com` / `admin` to log in. No real data is stored.

---

## Features

- **Automatic IP Detection** — Monitors IPv4 and IPv6 at configurable intervals
- **Immediate Sync** — Changes made in the UI are pushed to Cloudflare instantly
- **Domain Management** — Register multiple Cloudflare zones and manage them in one place
- **Bulk Import** — Import DNS records from a legacy JSON format with dry-run preview
- **Audit Log** — Full activity history for every sync, add, edit, and delete
- **Discord Notifications** — Optional webhook alerts when your IP changes
- **Dark Mode** — System-aware theme with manual toggle
- **Docker-first** — One-command deployment, runs on anything from a Raspberry Pi to a cloud VPS

## Architecture

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS |
| Backend API | FastAPI (Python 3.12), SQLAlchemy, Pydantic |
| Background Worker | APScheduler — periodic IP monitoring and sync |
| Database | SQLite with persistent volume |
| Auth | Session cookies (HttpOnly, SameSite=strict, 30-min expiry) |

---

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- A Cloudflare account with at least one domain

### 1. Get a Cloudflare API Token

1. Go to [Cloudflare API Tokens](https://dash.cloudflare.com/profile/api-tokens)
2. Create a new **Custom Token** with these permissions:
   - `Zone → Zone → Read`
   - `Zone → DNS → Edit`
3. Scope it to specific zones for better security, or all zones for convenience
4. Copy the token

### 2. Clone and Configure

```bash
git clone https://github.com/dreadnought-0/Dreadnought-DDNS.git
cd Dreadnought-DDNS

# Copy the sample environment file
cp .env.sample .env

# Edit with your values
nano .env
```

Key variables to set in `.env`:

```env
# Required
CF_API_TOKEN=your_cloudflare_api_token_here
ADMIN_EMAIL=you@example.com
ADMIN_PASSWORD=ChangeThisPassword

# Generate a strong random key (Linux/Mac: openssl rand -hex 32)
SECRET_KEY=your-secret-key-here

# Optional
POLL_INTERVAL_SECONDS=300   # How often to check for IP changes (60–7200)
IPV6_ENABLED=false          # Set to true to also manage AAAA records
DISCORD_WEBHOOK_URL=        # Leave blank to disable
TZ=America/Denver           # Your timezone
```

### 3. Deploy

How you deploy depends on your environment. Choose the method that fits:

---

#### Option A — Coolify (recommended for cloud/VPS)

Coolify handles the data directory, permissions, TLS, and reverse proxy automatically.

1. Create a new **Docker Compose** resource in Coolify and point it at this repository
2. Set your environment variables in the Coolify UI (same variables as above)
3. Set the `NEXT_PUBLIC_API_URL` environment variable on the `web` service to the **public URL of your API service** (e.g. `https://ddns-api.yourdomain.com`)
4. Assign a domain to the `web` service and a domain to the `api` service
5. Deploy — Coolify manages everything else

> The `worker` service runs in the background and does not need a domain assigned to it.

---

#### Option B — Direct Docker Compose on Linux / Raspberry Pi

```bash
# Create the data directory with write permissions for the container
mkdir -p ./data
chmod 777 ./data

# Start all services
docker compose up -d

# Check everything is running
docker compose ps

# Follow logs
docker compose logs -f
```

> **Why the data directory step?** Docker needs write access to `./data` to create the SQLite database. This is handled automatically by Coolify and other PaaS platforms, but must be done manually on a bare Linux host. The included `setup.sh` script does this for you if you prefer: `chmod +x setup.sh && ./setup.sh`.

The app will be available at:
- **Web UI**: http://localhost:8082
- **API**: http://localhost:8081

You will need a reverse proxy (Nginx, Caddy, Traefik) in front of it to expose it publicly with HTTPS. See [DEPLOYMENT.md](DEPLOYMENT.md) for examples.

---

### 4. First Login

1. Open the web UI in your browser
2. Log in with the `ADMIN_EMAIL` and `ADMIN_PASSWORD` from your `.env`
3. Go to **Domains** and add your first Cloudflare domain (you'll need the Zone ID from your Cloudflare dashboard)
4. Go to **Records** and add the DNS records you want tracked

---

## Configuration Reference

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `CF_API_TOKEN` | *required* | Cloudflare API token (Zone:Read + DNS:Edit) |
| `ADMIN_EMAIL` | `admin@local` | Login email for the web UI |
| `ADMIN_PASSWORD` | `ChangeMe!` | Login password — change this |
| `SECRET_KEY` | *required* | Secret used to sign session tokens. Use `openssl rand -hex 32` to generate |
| `POLL_INTERVAL_SECONDS` | `300` | Seconds between automatic IP checks (60–7200) |
| `IPV6_ENABLED` | `false` | Enable IPv6 detection and AAAA record updates |
| `DISCORD_WEBHOOK_URL` | *(empty)* | Discord webhook for IP change / error notifications |
| `TZ` | `America/Denver` | Server timezone for log timestamps |

### Cloudflare Zone ID

Each domain you add requires its Zone ID, which you can find in the Cloudflare dashboard:

1. Go to your domain in Cloudflare
2. On the right-hand sidebar of the Overview page, copy the **Zone ID**
3. Paste it when adding the domain in Dreadnought

### TTL Behaviour

| Record type | TTL behaviour |
|---|---|
| Normal | Uses the value you set (1–86400 seconds). `1` = Cloudflare "Auto" |
| Proxied | Forced to Auto (300s) by Cloudflare regardless of your setting |

---

## Usage

### Adding a Domain

1. Go to **Domains → Add Domain**
2. Enter the domain name (e.g. `example.com`) and its Cloudflare Zone ID
3. Save — the domain is now available when adding records

### Adding DNS Records

1. Go to **Records → Add Record**
2. Select your domain from the dropdown
3. Enter the **Host** — use `@` for the root domain, or a subdomain name (e.g. `vpn`, `www`)
4. Choose **Type**: A (IPv4) or AAAA (IPv6)
5. Set **Proxied** and **TTL** as needed
6. Click **Create** — the record is immediately synced to Cloudflare with your current IP

### Bulk Import

1. Go to **Import**
2. Paste a JSON array of records (see format below)
3. Click **Preview Import** (dry run) to validate before committing
4. Uncheck "Dry run" and click **Import Records** to create them

```json
[
  { "domain": "example.com", "host": "vpn",  "ip_version": 4, "ttl": 300, "proxied": false },
  { "domain": "example.com", "host": "@",    "ip_version": 4, "ttl": 300, "proxied": true  },
  { "domain": "example.com", "host": "mail", "ip_version": 4, "ttl": 300, "proxied": false }
]
```

---

## Troubleshooting

### "Unable to open database file"

```
sqlite3.OperationalError: unable to open database file
```

The `./data` directory is missing or the container can't write to it.

```bash
docker compose down
mkdir -p ./data && chmod 777 ./data
docker compose up -d
```

### "Failed to resolve zone_id for domain"

- Verify your API token has `Zone → Zone → Read` permission
- Confirm the domain is active in your Cloudflare account
- Double-check the spelling of the domain name

### "Rate limit exceeded"

The system handles this automatically with exponential backoff. If it persists, increase `POLL_INTERVAL_SECONDS` or check whether another application is sharing the same API token.

### "CNAME record exists, cannot create A/AAAA record"

Cloudflare does not allow A/AAAA records on a name that already has a CNAME. Remove the CNAME from Cloudflare first, then add the record in Dreadnought.

### Container shows "unhealthy"

```bash
# Check logs for the specific service
docker compose logs api
docker compose logs web
docker compose logs worker

# Restart a specific service
docker compose restart api

# Rebuild from scratch
docker compose up -d --build
```

---

## Running Tests

```bash
cd backend
pip install -r requirements.txt
pytest
```

---

## Contributing

Contributions are very welcome! Whether it's a bug fix, new feature, documentation improvement, or a review — please feel free to open an issue to discuss ideas or submit a pull request directly.

---

## Support

- **Questions / Ideas**: [GitHub Discussions](https://github.com/dreadnought-0/Dreadnought-DDNS/discussions)
- **Bug Reports**: [GitHub Issues](https://github.com/dreadnought-0/Dreadnought-DDNS/issues)

---

## License

MIT License