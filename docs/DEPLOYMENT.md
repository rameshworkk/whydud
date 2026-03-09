# WHYDUD — Deployment Guide

> Complete reference for deploying, redeploying, and troubleshooting the Whydud platform.
> Complements `SERVER_INFRASTRUCTURE.md` (architecture) and `ARCHITECTURE.md` (system design).
> Last updated: 2026-03-03 after successful primary + replica node deployment.

---

## Table of Contents

1. [Architecture Quick Reference](#1-architecture-quick-reference)
2. [File Path Reference](#2-file-path-reference)
3. [Version Matrix](#3-version-matrix)
4. [Known Version Conflicts](#4-known-version-conflicts)
5. [Prerequisites](#5-prerequisites)
6. [Environment Variables](#6-environment-variables)
7. [First Deploy — Primary Node](#7-first-deploy--primary-node)
8. [First Deploy — Replica Node](#8-first-deploy--replica-node)
9. [Subsequent Deploys](#9-subsequent-deploys)
10. [Docker Build Details](#10-docker-build-details)
11. [Primary vs Replica Differences](#11-primary-vs-replica-differences)
12. [Celery Configuration](#12-celery-configuration)
13. [PostgreSQL Configuration](#13-postgresql-configuration)
14. [Caddyfile Configuration](#14-caddyfile-configuration)
15. [Django Production Settings](#15-django-production-settings)
16. [Troubleshooting](#16-troubleshooting)
17. [Known Bottlenecks & Improvements](#17-known-bottlenecks--improvements)
18. [Useful Commands Reference](#18-useful-commands-reference)

---

## 1. Architecture Quick Reference

```
                    ┌──────────────────┐
                    │   Cloudflare     │
                    │   DNS + CDN      │
                    │   SSL (Full      │
                    │   strict)        │
                    └────────┬─────────┘
                             │ HTTPS (port 443)
              ┌──────────────┴──────────────┐
              ▼                             ▼
   ┌──────────────────┐         ┌──────────────────┐
   │  PRIMARY NODE    │         │  REPLICA NODE    │
   │  95.111.232.70   │         │  46.250.237.93   │
   │  12GB / 6 vCPU   │ WG VPN │  8GB / 4 vCPU    │
   │  10.8.0.1        │◄──────►│  10.8.0.2        │
   └──────────────────┘ :51820 └──────────────────┘
```

### Service Port Map

| Service | Container Name | Port (host) | Port (container) | Notes |
|---|---|---|---|---|
| Caddy | whydud-caddy | 80, 443 | 80, 443 | Reverse proxy + TLS |
| Backend (Gunicorn) | whydud-backend | — | 8000 | Internal only |
| Frontend (Next.js) | whydud-frontend | — | 3000 | Internal only |
| PostgreSQL | whydud-postgres | 127.0.0.1:5432, 10.8.0.1:5432 | 5432 | Primary exposes on WG IP |
| Redis | whydud-redis | 127.0.0.1:6379, 10.8.0.1:6379 | 6379 | Primary exposes on WG IP |
| Meilisearch | whydud-meilisearch | 127.0.0.1:7700 | 7700 | Localhost only |
| Celery Worker | whydud-celery-worker | — | 8000 (unused) | Primary: default,scoring,alerts,email |
| Celery Beat | whydud-celery-beat | — | 8000 (unused) | Primary only (scheduler) |
| Celery Scraping | whydud-celery-scraping | — | 8000 (unused) | Replica only |

### Memory Budget

| Service | Primary (12GB) | Replica (8GB) |
|---|---|---|
| PostgreSQL | 3 GB | 2 GB |
| Redis | 768 MB | 512 MB |
| Meilisearch | 1 GB | 1 GB |
| Backend | 2 GB | 1.5 GB |
| Frontend | 1 GB | 1 GB |
| Celery Worker | 1 GB | — |
| Celery Beat | 256 MB | — |
| Celery Scraping | — | 2 GB |
| Caddy | 128 MB | 128 MB |
| **Total** | **~9.15 GB** | **~8.14 GB** |

---

## 2. File Path Reference

### Repository Files (deployment-critical)

```
whydud/
├── docker-compose.primary.yml          # Primary node compose (8 services)
├── docker-compose.replica.yml          # Replica node compose (7 services, no beat)
├── deploy.sh                           # Deployment script
├── .env.example                        # Environment variable template
├── .gitignore                          # Includes docker/certs/, init-replication.sql
│
├── docker/
│   ├── Dockerfiles/
│   │   ├── backend.Dockerfile          # Python 3.12-slim, multi-stage
│   │   └── frontend.Dockerfile         # Node 22-alpine, multi-stage
│   ├── Caddyfile.cloudflare            # Production Caddy config (TLS + routes)
│   ├── certs/                          # GITIGNORED — Cloudflare Origin Certs
│   │   ├── origin.pem                  # Certificate (create on server)
│   │   └── origin-key.pem             # Private key (create on server)
│   └── postgres/
│       ├── primary.conf                # PostgreSQL production tuning
│       ├── pg_hba.conf                 # Auth rules (Docker, WireGuard, replication)
│       ├── init.sql                    # Schema creation (runs on first volume init)
│       └── init-replication.sh         # Creates replicator user (runs on first init)
│
├── backend/
│   ├── whydud/
│   │   ├── settings/
│   │   │   ├── base.py                 # All apps, middleware, celery, security
│   │   │   ├── prod.py                 # DATABASE_URL, CSRF, CORS, WhiteNoise
│   │   │   └── dev.py                  # Local development overrides
│   │   ├── db_router.py                # Read/write split for replica node
│   │   ├── celery.py                   # 5 queues, 10 beat tasks
│   │   ├── wsgi.py                     # WSGI entry point
│   │   └── urls.py                     # Root URL routing (14 paths)
│   ├── requirements/
│   │   ├── base.txt                    # 25 core packages (source of truth)
│   │   ├── prod.txt                    # +3 packages (gunicorn, whitenoise, sentry)
│   │   ├── dev.txt                     # +10 packages (pytest, ruff, mypy)
│   │   └── local-freeze.txt           # 123 packages (OUTDATED, do not use for prod)
│   └── common/
│       └── app_settings.py             # Tuneable config values
│
├── frontend/
│   ├── package.json                    # All frontend dependencies
│   ├── next.config.ts                  # Standalone output, image domains, rewrites
│   ├── tsconfig.json                   # TypeScript strict config
│   ├── postcss.config.mjs              # Tailwind v4 PostCSS plugin
│   └── src/lib/api/client.ts           # API client (INTERNAL_API_URL for SSR)
│
└── docs/
    ├── DEPLOYMENT.md                   # This file
    ├── SERVER_INFRASTRUCTURE.md        # Network, WireGuard, failover procedures
    └── ARCHITECTURE.md                 # System architecture
```

### Server Paths

```
/opt/whydud/
├── .env                                # Production env file (NOT in git)
└── whydud/                             # Git repo clone
    ├── docker/certs/                   # TLS certificates (created manually)
    └── ...                             # All repo files

/opt/scripts/
├── backup-db.sh                        # Daily 3 AM cron
├── docker-cleanup.sh                   # Weekly Sunday 4 AM cron
└── wg-monitor.sh                       # Every 5 min cron

/opt/backups/postgres/                  # Database backups (7-day retention)
/etc/wireguard/wg0.conf                # WireGuard tunnel config
/etc/systemd/system/whydud.service     # Auto-start on reboot
```

---

## 3. Version Matrix

### Docker Images

| Image | Tag | Purpose |
|---|---|---|
| python | 3.12-slim | Backend base |
| node | 22-alpine | Frontend base |
| timescale/timescaledb | latest-pg16 | PostgreSQL 16 + TimescaleDB |
| redis | 7-alpine | Cache + Celery broker |
| getmeili/meilisearch | v1.7 | Product search |
| caddy | 2-alpine | Reverse proxy |

### Backend Python Packages (base.txt — source of truth)

| Package | Version | Purpose |
|---|---|---|
| Django | 5.2.11 | Web framework |
| djangorestframework | 3.16.1 | REST API |
| django-cors-headers | 4.9.0 | CORS middleware |
| django-allauth | 65.14.3 | Auth + Google OAuth (pinned) |
| PyJWT | 2.10.1 | JWT for allauth OAuth |
| psycopg[binary] | 3.3.3 | PostgreSQL 16 driver (psycopg3) |
| celery[redis] | 5.6.2 | Task queue |
| django-celery-beat | 2.8.1 | Periodic task scheduler |
| django-celery-results | 2.6.0 | Task result storage |
| flower | 2.0.1 | Celery monitoring dashboard |
| redis | 5.2.1 | Redis client |
| meilisearch | 0.40.0 | Search client |
| spacy | 3.7.5 | NLP for review analysis |
| textblob | 0.19.0 | Sentiment analysis |
| numpy | 1.26.4 | Numerical (PINNED for spacy) |
| pandas | 2.3.3 | Data processing |
| scikit-learn | 1.5.1 | ML models |
| scrapy | 2.14.1 | Web scraping framework |
| playwright | 1.58.0 | Browser automation |
| scrapy-playwright | 0.0.46 | Scrapy + Playwright bridge |
| cryptography | 46.0.5 | AES-256-GCM encryption |
| razorpay | 2.0.0 | Payment gateway |
| nh3 | 0.3.3 | HTML sanitization |
| resend | 2.23.0 | Transactional email API |
| httpx | 0.27.0 | HTTP client |
| pydantic | 2.12.5 | Validation |
| structlog | 25.5.0 | JSON structured logging |
| python-decouple | 3.8 | Config from env |
| python-dotenv | 1.2.1 | .env file loading |
| Pillow | 12.1.0 | Image processing |

### Backend Production-Only Packages (prod.txt)

| Package | Version | Purpose |
|---|---|---|
| gunicorn | 23.0.0 | WSGI server |
| whitenoise | 6.11.0 | Static file serving |
| sentry-sdk[django] | 2.12.0 | Error monitoring |

### Frontend Packages (package.json)

| Package | Version | Purpose |
|---|---|---|
| next | 15.1.0 | React framework (App Router) |
| react | 19.0.0 | UI library |
| react-dom | 19.0.0 | React DOM renderer |
| @radix-ui/react-avatar | ^1.1.11 | Avatar component |
| @radix-ui/react-checkbox | ^1.3.3 | Checkbox |
| @radix-ui/react-dialog | ^1.1.15 | Modal dialogs |
| @radix-ui/react-dropdown-menu | ^2.1.16 | Dropdown menus |
| @radix-ui/react-label | ^2.1.8 | Form labels |
| @radix-ui/react-popover | ^1.1.4 | Popovers |
| @radix-ui/react-progress | ^1.1.8 | Progress bars |
| @radix-ui/react-scroll-area | ^1.2.2 | Scroll containers |
| @radix-ui/react-select | ^2.2.6 | Select dropdowns |
| @radix-ui/react-separator | ^1.1.8 | Dividers |
| @radix-ui/react-slider | ^1.3.6 | Range sliders |
| @radix-ui/react-slot | ^1.2.4 | Slot pattern |
| @radix-ui/react-switch | ^1.2.6 | Toggle switches |
| @radix-ui/react-tabs | ^1.1.13 | Tab panels |
| @radix-ui/react-tooltip | ^1.2.8 | Tooltips |
| class-variance-authority | ^0.7.1 | Component variants |
| clsx | ^2.1.1 | Class name utility |
| date-fns | ^4.1.0 | Date formatting |
| lucide-react | ^0.460.0 | Icons |
| recharts | ^2.13.3 | Charts |
| tailwind-merge | ^2.5.4 | Tailwind class merging |
| zustand | ^5.0.2 | State management |

### Frontend Dev Dependencies

| Package | Version | Purpose |
|---|---|---|
| tailwindcss | ^4.0.0 | CSS framework (v4) |
| @tailwindcss/postcss | ^4.0.0 | PostCSS plugin |
| postcss | ^8.5.0 | CSS transforms |
| typescript | ^5.7.0 | Type checking |
| eslint | ^9.0.0 | Linting |
| eslint-config-next | 15.1.0 | Next.js ESLint rules |
| @types/node | ^22.0.0 | Node.js types |
| @types/react | ^19.0.0 | React types |
| @types/react-dom | ^19.0.0 | React DOM types |

---

## 4. Known Version Conflicts

### 1. numpy / spacy Binary Incompatibility (CRITICAL)

**Symptom:** `ImportError` when importing spacy in production.
**Cause:** spacy 3.7.5 ships with pre-compiled Cython extensions linked against numpy 1.x ABI. numpy 2.x broke binary compatibility.
**Fix:** Pin `numpy==1.26.4` in base.txt (done in commit `d14e4ab`).
**Warning:** `local-freeze.txt` still lists `numpy==2.4.1` — do NOT use freeze files for production installs. Always use `base.txt` + `prod.txt`.

### 2. redis Client Version Mismatch

**Symptom:** Potential connection issues between celery and redis.
**Cause:** `base.txt` pins `redis==5.2.1`, but `local-freeze.txt` has `redis==7.1.0`.
**Fix:** Use `base.txt` as source of truth. Freeze files are outdated.

### 3. django-allauth Version Pin

**Symptom:** OAuth callback errors, template rendering failures.
**Cause:** Newer allauth versions changed internal APIs. Pinned to 65.14.3 matching the working local env (commit `ba6a117`).
**Fix:** Keep pinned until explicitly tested with a newer version.

### 4. Missing PyJWT

**Symptom:** `ModuleNotFoundError: No module named 'jwt'` during Google OAuth.
**Cause:** allauth Google OAuth requires PyJWT for token handling, but it wasn't in requirements.
**Fix:** Added `PyJWT==2.10.1` to base.txt (commit `0237619`).

### 5. psycopg2 vs psycopg3

**Cause:** `local-freeze.txt` includes both `psycopg-binary==3.3.3` (psycopg3) and `psycopg2-binary==2.9.11` (legacy).
**Status:** Production uses psycopg3 only (`psycopg[binary]==3.3.3`). psycopg2 is a leftover from local dev and is not needed.

### 6. Freeze File Reliability

**`local-freeze.txt`** and **`lock.txt`** are pip freeze snapshots from a local dev environment. They contain 123 packages including dev-only tools (django-debug-toolbar, boto3, stripe, drf-yasg, etc.) and version conflicts with base.txt. **Never use these for production deployment.** Always install from `base.txt` + `prod.txt`.

---

## 5. Prerequisites

### Server Setup (both nodes)

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker deploy

# Install Docker Compose (v2 — included with Docker Engine 24+)
docker compose version  # should show v2.x

# Install Git
sudo apt install -y git

# Create deploy user
sudo adduser deploy
sudo usermod -aG docker deploy
sudo usermod -aG sudo deploy

# SSH hardening
sudo sed -i 's/^#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo sed -i 's/^PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sudo systemctl restart sshd
```

### Firewall (both nodes)

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP (Caddy)
sudo ufw allow 443/tcp     # HTTPS (Caddy)
sudo ufw allow 51820/udp   # WireGuard
sudo ufw enable
sudo ufw status
```

### WireGuard VPN

**Primary (95.111.232.70) — `/etc/wireguard/wg0.conf`:**
```ini
[Interface]
Address = 10.8.0.1/24
ListenPort = 51820
PrivateKey = <PRIMARY_PRIVATE_KEY>

[Peer]
PublicKey = <REPLICA_PUBLIC_KEY>
AllowedIPs = 10.8.0.2/32
Endpoint = 46.250.237.93:51820
PersistentKeepalive = 25
```

**Replica (46.250.237.93) — `/etc/wireguard/wg0.conf`:**
```ini
[Interface]
Address = 10.8.0.2/24
ListenPort = 51820
PrivateKey = <REPLICA_PRIVATE_KEY>

[Peer]
PublicKey = <PRIMARY_PUBLIC_KEY>
AllowedIPs = 10.8.0.1/32
Endpoint = 95.111.232.70:51820
PersistentKeepalive = 25
```

```bash
# Generate keys (on each node)
wg genkey | tee privatekey | wg pubkey > publickey

# Start WireGuard
sudo systemctl enable wg-quick@wg0
sudo systemctl start wg-quick@wg0

# Verify tunnel
ping 10.8.0.2  # from primary
ping 10.8.0.1  # from replica
```

### Directory Structure (both nodes)

```bash
sudo mkdir -p /opt/whydud
sudo mkdir -p /opt/scripts
sudo mkdir -p /opt/backups/postgres
sudo chown -R deploy:deploy /opt/whydud /opt/scripts /opt/backups
```

### Clone Repository

```bash
cd /opt/whydud
git clone git@github.com:rameshworkk/whydud.git whydud
```

### Cloudflare Origin Certificate

1. Go to **Cloudflare Dashboard → SSL/TLS → Origin Server → Create Certificate**
2. Let Cloudflare generate key type: RSA (2048)
3. Hostnames: `whydud.com, *.whydud.com`
4. Certificate validity: 15 years
5. Click **Create** — copy both certificate and private key

```bash
# On server:
mkdir -p /opt/whydud/whydud/docker/certs
nano /opt/whydud/whydud/docker/certs/origin.pem       # paste certificate
nano /opt/whydud/whydud/docker/certs/origin-key.pem    # paste private key
chmod 600 /opt/whydud/whydud/docker/certs/origin-key.pem
```

6. In Cloudflare Dashboard → **SSL/TLS → Overview → Set to "Full (strict)"**

### Systemd Service (auto-start on reboot)

Create `/etc/systemd/system/whydud.service`:
```ini
[Unit]
Description=Whydud Platform
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/whydud/whydud
ExecStart=/usr/bin/docker compose -f docker-compose.primary.yml up -d
ExecStop=/usr/bin/docker compose -f docker-compose.primary.yml down
User=deploy
Group=deploy

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable whydud
```

Replace `primary` with `replica` on the replica node.

### Cron Jobs

```bash
# Edit crontab
crontab -e

# Add these entries:
0 3 * * * /opt/scripts/backup-db.sh          # Daily DB backup at 3 AM
0 4 * * 0 /opt/scripts/docker-cleanup.sh     # Weekly Docker cleanup Sunday 4 AM
*/5 * * * * /opt/scripts/wg-monitor.sh       # WireGuard health check every 5 min
```

---

## 6. Environment Variables

### Complete .env Template

Copy to `/opt/whydud/.env` on each server. The compose files reference this via `env_file: ../.env`.

```bash
# ============================================================
# Whydud — Production Environment Variables
# ============================================================

# ---- Django ----
DJANGO_SECRET_KEY=<generate: python -c "import secrets; print(secrets.token_urlsafe(50))">
DJANGO_SETTINGS_MODULE=whydud.settings.prod
DJANGO_ALLOWED_HOSTS=whydud.com,www.whydud.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://whydud.com,https://www.whydud.com

# ---- PostgreSQL ----
POSTGRES_DB=whydud
POSTGRES_USER=whydud
POSTGRES_PASSWORD=<strong random password>
REPLICATOR_PASSWORD=<strong random password>   # PRIMARY only — creates replication user

# ---- Redis ----
REDIS_PASSWORD=<strong random password>

# ---- Meilisearch ----
MEILISEARCH_MASTER_KEY=<min 32 chars random string>

# ---- Encryption Keys ----
# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
EMAIL_ENCRYPTION_KEY=<64-char hex string>
OAUTH_ENCRYPTION_KEY=<64-char hex string>

# ---- Frontend ----
NEXT_PUBLIC_API_URL=https://whydud.com
NEXT_PUBLIC_SITE_URL=https://whydud.com

# ---- Google OAuth (optional) ----
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

# ---- Resend (transactional email) ----
RESEND_API_KEY=

# ---- Cloudflare Email Worker ----
CLOUDFLARE_EMAIL_WEBHOOK_SECRET=

# ---- Razorpay (payments) ----
RAZORPAY_KEY_ID=
RAZORPAY_KEY_SECRET=

# ---- Sentry (error monitoring) ----
SENTRY_DSN=

# ---- Scraping (REPLICA node) ----
SCRAPING_PROXY_LIST=http://user:pass@gw.dataimpulse.com:823
SCRAPING_PROXY_TYPE=rotating
SCRAPING_PROXY_BAN_COOLDOWN_BASE=3
SCRAPING_PROXY_BAN_MAX_COOLDOWN=15

# ---- Discord Notifications ----
DISCORD_WEBHOOK_URL=               # Discord webhook for Celery task notifications (both nodes)
```

### Variable Scope

| Variable | Primary | Replica | Notes |
|---|---|---|---|
| DJANGO_SECRET_KEY | SAME | SAME | Must match across nodes |
| POSTGRES_PASSWORD | SAME | SAME | Shared database credentials |
| REPLICATOR_PASSWORD | YES | NO | Only primary creates repl user |
| REDIS_PASSWORD | SAME | SAME | Replica connects to primary Redis |
| DATABASE_URL | Set by compose | Set by compose | Points to local postgres |
| DATABASE_WRITE_URL | NOT SET | Set by compose | Replica → primary WG IP |
| CELERY_BROKER_URL | Set by compose (local) | Set by compose (10.8.0.1) | Replica uses primary Redis |
| NODE_ROLE | primary | replica | Set by compose |
| SCRAPING_PROXY_* | Optional | YES | Scraping runs on replica |
| DISCORD_WEBHOOK_URL | YES | YES | Celery task notifications to Discord |

### Key Generation Commands

```bash
# Django secret key
python -c "import secrets; print(secrets.token_urlsafe(50))"

# Encryption keys (hex format, 64 chars)
python -c "import secrets; print(secrets.token_hex(32))"

# Redis/Meilisearch passwords
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## 7. First Deploy — Primary Node

Run every command in sequence. Do not skip steps.

### Step 1: Environment Setup

```bash
# SSH into primary
ssh deploy@95.111.232.70

# Verify prerequisites
docker --version        # Docker 24+
docker compose version  # v2.x
git --version
sudo ufw status         # ports 22, 80, 443, 51820 open
```

### Step 2: Clone and Configure

```bash
cd /opt/whydud
git clone git@github.com:rameshworkk/whydud.git whydud
cd whydud

# Create environment file
cp .env.example /opt/whydud/.env
nano /opt/whydud/.env   # Fill in ALL production values
```

### Step 3: Create TLS Certificates

```bash
# Create certs directory
mkdir -p docker/certs

# Paste Cloudflare Origin Certificate and Key (see Prerequisites section)
nano docker/certs/origin.pem
nano docker/certs/origin-key.pem
chmod 600 docker/certs/origin-key.pem
```

### Step 4: Build Docker Images

```bash
docker compose -f docker-compose.primary.yml build
```

**Expected output:** Each stage runs (base, deps, builder/production). First build takes 5-10 minutes.

**If you see "CACHED" on all layers after a code change:**
```bash
docker compose -f docker-compose.primary.yml build --no-cache backend
```

### Step 5: Start Infrastructure Services

```bash
docker compose -f docker-compose.primary.yml up -d postgres redis meilisearch
```

**Wait for health checks:**
```bash
# Check all three are healthy
docker compose -f docker-compose.primary.yml ps
```

Expected: postgres (healthy), redis (healthy), meilisearch (healthy). Wait ~30 seconds.

### Step 6: Run Migrations

```bash
docker compose -f docker-compose.primary.yml run --rm backend python manage.py migrate --no-input
```

**Expected output:** `Applying <app>.0001_initial... OK` for all 27 migrations across 24 apps.

**If migrations fail with TimescaleDB errors**, see [Troubleshooting #9 and #10](#16-troubleshooting).

### Step 7: Create Superuser

```bash
docker compose -f docker-compose.primary.yml run --rm backend python manage.py createsuperuser
```

### Step 8: Seed Data (optional)

```bash
docker compose -f docker-compose.primary.yml run --rm backend python manage.py seed_data
docker compose -f docker-compose.primary.yml run --rm backend python manage.py seed_preference_schemas
```

### Step 9: Start All Services

```bash
docker compose -f docker-compose.primary.yml up -d
```

**Expected:** All 8 containers start (postgres, redis, meilisearch, backend, frontend, celery-worker, celery-beat, caddy).

### Step 10: Verify

```bash
# All containers running?
docker compose -f docker-compose.primary.yml ps

# Backend responds?
docker compose -f docker-compose.primary.yml exec backend curl -sf http://localhost:8000/api/v1/products/

# Caddy serves frontend?
curl -v http://localhost:80

# Check for errors
docker compose -f docker-compose.primary.yml logs backend --tail=50
docker compose -f docker-compose.primary.yml logs caddy --tail=50
docker compose -f docker-compose.primary.yml logs frontend --tail=20
```

### Step 11: Cloudflare SSL

In Cloudflare Dashboard: **SSL/TLS → Overview → Full (strict)**

### Step 12: Verify from Internet

```bash
curl -v https://whydud.com
curl -v https://whydud.com/api/v1/products/
```

---

## 8. First Deploy — Replica Node

> Replica deployment completed 2026-03-03. PostgreSQL streaming replication verified working.

### Step 1: Same as Primary Steps 1-3

Clone repo, create .env (with replica-specific values), create certs.

### Step 2: Verify WireGuard

```bash
# From replica, can you reach primary?
ping 10.8.0.1

# Can you reach primary PostgreSQL?
nc -zv 10.8.0.1 5432

# Can you reach primary Redis?
nc -zv 10.8.0.1 6379
```

### Step 3: Bootstrap PostgreSQL Replica

On the PRIMARY, create the replication slot:
```bash
docker compose -f docker-compose.primary.yml exec postgres psql -U whydud -d whydud -c \
  "SELECT * FROM pg_create_physical_replication_slot('replica_slot');"
```

On the REPLICA:
```bash
# Remove any existing postgres data
docker volume rm whydud_postgres_data 2>/dev/null || true

# Bootstrap from primary via pg_basebackup
docker run --rm \
  -v whydud_postgres_data:/var/lib/postgresql/data \
  --add-host=primary:10.8.0.1 \
  timescale/timescaledb:latest-pg16 \
  pg_basebackup -h 10.8.0.1 -U replicator -D /var/lib/postgresql/data \
  -Fp -Xs -P -R -S replica_slot
```

### Step 4: Build and Start

```bash
docker compose -f docker-compose.replica.yml build
docker compose -f docker-compose.replica.yml up -d
```

### Step 5: Verify Replication

On the PRIMARY:
```sql
SELECT * FROM pg_stat_replication;
-- Should show one row with state='streaming'

SELECT slot_name, active FROM pg_replication_slots;
-- Should show replica_slot, active=true
```

On the REPLICA:
```sql
SELECT pg_is_in_recovery();
-- Should return true (this is a replica)

SELECT pg_last_wal_receive_lsn(), pg_last_wal_replay_lsn();
-- Both should be close to each other (low lag)
```

---

## 9. Subsequent Deploys

### Quick Redeploy (code changes only)

```bash
cd /opt/whydud/whydud
git pull origin master
docker compose -f docker-compose.primary.yml build backend
docker compose -f docker-compose.primary.yml up -d --force-recreate backend celery-worker celery-beat
```

**IMPORTANT:** `--force-recreate` is required when Docker shows "Running" instead of "Started". Without it, Docker reuses the old container even if the image changed.

### When Dockerfile Changes

```bash
docker compose -f docker-compose.primary.yml build --no-cache backend
docker compose -f docker-compose.primary.yml up -d --force-recreate backend celery-worker celery-beat
```

### When Requirements Change

```bash
# Must rebuild from scratch (cached pip install won't pick up changes)
docker compose -f docker-compose.primary.yml build --no-cache backend
docker compose -f docker-compose.primary.yml up -d --force-recreate backend celery-worker celery-beat
```

### When Frontend Changes

```bash
docker compose -f docker-compose.primary.yml build frontend
docker compose -f docker-compose.primary.yml up -d --force-recreate frontend
```

### When Caddyfile Changes

```bash
# No build needed — Caddyfile is mounted as a volume
docker compose -f docker-compose.primary.yml restart caddy
```

### When docker-compose.yml Changes

```bash
docker compose -f docker-compose.primary.yml up -d
# Docker detects config changes and recreates affected services
```

### Migration Workflow

```bash
# ALWAYS on PRIMARY only — NEVER run migrations on replica
docker compose -f docker-compose.primary.yml run --rm backend python manage.py migrate --no-input

# Check migration status
docker compose -f docker-compose.primary.yml run --rm backend python manage.py showmigrations
```

### Using deploy.sh

```bash
# First deploy
./deploy.sh primary --first-run

# Subsequent deploys
./deploy.sh primary
```

---

## 10. Docker Build Details

### Backend Dockerfile (docker/Dockerfiles/backend.Dockerfile)

```
Stage: base (python:3.12-slim)
  ├── WORKDIR /app
  ├── Install system deps: libpq-dev gcc g++ libffi-dev curl
  └── Set PYTHONDONTWRITEBYTECODE=1, PYTHONUNBUFFERED=1, PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

Stage: deps (extends base)
  ├── COPY requirements/base.txt + prod.txt
  ├── pip install -r requirements/prod.txt
  ├── python -m spacy download en_core_web_sm    ← downloads 12MB NLP model
  └── playwright install-deps chromium && playwright install chromium
      └── Installs to /ms-playwright (PLAYWRIGHT_BROWSERS_PATH env var)
      └── chmod -R o+rx /ms-playwright (readable by non-root whydud user)

Stage: production (extends base + deps)
  ├── COPY backend/ .                            ← copies all backend code
  ├── RUN collectstatic                          ← requires DJANGO_SECRET_KEY build arg
  ├── RUN useradd whydud                         ← non-root user
  └── CMD: gunicorn whydud.wsgi:application
```

**Build arg for collectstatic:** The Dockerfile passes `DJANGO_SECRET_KEY=build-only-collectstatic-key` at build time so Django can initialize enough to collect static files without a real secret.

**Playwright browsers path:** `PLAYWRIGHT_BROWSERS_PATH=/ms-playwright` is set in the base stage ENV. This ensures `playwright install chromium` (which runs as root during build) installs to a shared path, not `/root/.cache/ms-playwright/`. The production stage runs as `USER whydud` — without this, Playwright would look in `/home/whydud/.cache/ms-playwright/` and fail. See [Troubleshooting #19](#issue-19-playwright-chromium-binary-not-found-non-root-user).

**Docker layer caching gotcha:** The `COPY backend/ .` step computes a checksum of ALL files in `backend/`. If you changed a file but Docker's build cache has a matching checksum (unlikely but possible with Git), use `--no-cache`.

### Frontend Dockerfile (docker/Dockerfiles/frontend.Dockerfile)

```
Stage: base (node:22-alpine)
  └── WORKDIR /app, NEXT_TELEMETRY_DISABLED=1

Stage: deps (extends base)
  ├── COPY package.json + package-lock.json
  └── npm ci --legacy-peer-deps              ← legacy-peer-deps for React 19 compat

Stage: builder (extends base + deps)
  ├── COPY frontend/ .
  ├── ARG NEXT_PUBLIC_API_URL, NEXT_PUBLIC_SITE_URL   ← baked into JS bundle at build
  └── npm run build                                    ← produces .next/standalone

Stage: production (extends base)
  ├── COPY .next/standalone ./
  ├── COPY .next/static ./.next/static
  ├── COPY public ./public
  ├── USER nextjs (uid 1001)
  └── CMD: node server.js                    ← standalone Next.js server
```

**NEXT_PUBLIC_* build args:** These are baked into the JavaScript bundle at build time. Changing them requires a full frontend rebuild. They default to `https://whydud.com`.

### Missing .dockerignore

The project currently has no `.dockerignore` file. This means Docker sends the entire build context (including `.git/`, `node_modules/`, `__pycache__/`, etc.) to the daemon. For now the context is small (~15KB), but it will grow. See [Bottleneck #1](#17-known-bottlenecks--improvements).

---

## 11. Primary vs Replica Differences

| Aspect | Primary | Replica |
|---|---|---|
| **Compose file** | `docker-compose.primary.yml` | `docker-compose.replica.yml` |
| **Server** | 95.111.232.70 (12GB/6CPU) | 46.250.237.93 (8GB/4CPU) |
| **WireGuard IP** | 10.8.0.1 | 10.8.0.2 |
| **PostgreSQL role** | PRIMARY (read/write) | REPLICA (read-only) |
| **PostgreSQL ports** | 127.0.0.1:5432 + 10.8.0.1:5432 | 127.0.0.1:5432 only |
| **Redis ports** | 127.0.0.1:6379 + 10.8.0.1:6379 | 127.0.0.1:6379 only |
| **PostgreSQL memory** | 3 GB | 2 GB |
| **Redis memory** | 768 MB (maxmemory 512mb) | 512 MB (maxmemory 384mb) |
| **Backend workers** | 3 workers × 2 threads | 2 workers × 2 threads |
| **Backend memory** | 2 GB | 1.5 GB |
| **NODE_ROLE** | `primary` | `replica` |
| **DATABASE_URL** | postgres://whydud:pass@postgres:5432/whydud | Same (local replica) |
| **DATABASE_WRITE_URL** | NOT SET | postgres://whydud:pass@10.8.0.1:5432/whydud |
| **CELERY_BROKER_URL** | redis://:pass@redis:6379/0 (local) | redis://:pass@10.8.0.1:6379/0 (primary) |
| **Celery worker** | celery-worker: default,scoring,alerts,email | celery-scraping: scraping only |
| **Celery beat** | YES (scheduler) | NO |
| **Migrations** | YES (on every deploy) | NEVER (replicated from primary) |
| **init-replication.sh** | YES (creates replicator user) | NO |
| **primary.conf** | YES (WAL, replication settings) | NO (uses default config) |
| **pg_hba.conf** | YES (allows 10.8.0.2 replication) | NO |
| **SCRAPING_PROXY_*** | Optional | Required |

---

## 12. Celery Configuration

### Queues (5 total)

| Queue | Exchange | Routing Key | Node |
|---|---|---|---|
| default | default | default | Primary |
| scoring | scoring | scoring | Primary |
| alerts | alerts | alerts | Primary |
| email | email | email | Primary |
| scraping | scraping | scraping | Replica |

### Discord Webhook Notifications

All Celery task completions, failures, and retries send notifications to Discord via `DISCORD_WEBHOOK_URL`. Registered via Celery signals (`task_success`, `task_failure`, `task_retry`) in `celery.py`. Both primary and replica workers send notifications. Internal tasks like `celery.backend_cleanup` are filtered out.

### Beat Schedule (10 tasks — runs on PRIMARY only)

| Name | Task | Schedule | Queue |
|---|---|---|---|
| publish-pending-reviews-hourly | `apps.reviews.tasks.publish_pending_reviews` | Every hour at :00 | default |
| update-reviewer-profiles-weekly | `apps.reviews.tasks.update_reviewer_profiles` | Monday 00:00 UTC | scoring |
| check-price-alerts-4h | `apps.pricing.tasks.check_price_alerts` | Every 4h at :00 | alerts |
| scrape-amazon-in-6h | `apps.scraping.tasks.run_marketplace_spider` (amazon-in) | 00,06,12,18 UTC | scraping |
| scrape-flipkart-6h | `apps.scraping.tasks.run_marketplace_spider` (flipkart) | 03,09,15,21 UTC | scraping |
| meilisearch-full-reindex-daily | `apps.search.tasks.full_reindex` | 01:00 UTC | default |
| dudscore-full-recalc-monthly | `apps.scoring.tasks.full_dudscore_recalculation` | 1st of month, 03:00 UTC | scoring |
| detect-deals-2h | `apps.deals.tasks.detect_blockbuster_deals` | Every 2h at :00 | scoring |
| scrape-amazon-in-reviews-daily | `apps.scraping.tasks.run_review_spider` (amazon-in) | 04:00 UTC | scraping |
| scrape-flipkart-reviews-daily | `apps.scraping.tasks.run_review_spider` (flipkart) | 07:00 UTC | scraping |

### Worker Commands

**Primary:**
```bash
celery -A whydud worker --loglevel=info --concurrency=2 --queues=default,scoring,alerts,email --hostname=primary@%h
celery -A whydud beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

**Replica:**
```bash
celery -A whydud worker --loglevel=info --concurrency=2 --queues=scraping --hostname=scraping@%h
```

---

## 13. PostgreSQL Configuration

### primary.conf (full file with explanations)

```ini
# Required for TimescaleDB — MUST be first or CREATE EXTENSION fails
shared_preload_libraries = 'timescaledb'

# WAL (Write-Ahead Log) — enables streaming replication
wal_level = replica                  # Enough for streaming replication
max_wal_senders = 5                  # Max concurrent replication connections
wal_keep_size = '1GB'                # Keep 1GB WAL for replica catch-up
hot_standby = on                     # Allow reads on replica
synchronous_commit = on              # Durability guarantee
wal_compression = on                 # Reduce WAL size over WireGuard

# Memory tuning for 12GB server
shared_buffers = '1GB'               # 25% of available RAM for DB
effective_cache_size = '3GB'         # OS cache hint for query planner
work_mem = '32MB'                    # Per-query sort/hash memory
maintenance_work_mem = '256MB'       # VACUUM, CREATE INDEX, etc.

# Connections
max_connections = 100                # Sufficient for 2-3 app servers
listen_addresses = '*'               # Accept connections on all IPs

# Logging
log_min_duration_statement = 1000    # Log queries slower than 1 second
log_connections = on                 # Log connection attempts
log_disconnections = on              # Log disconnections
log_line_prefix = '%m [%p] %q%u@%d ' # Timestamp, PID, user@database
```

### pg_hba.conf (full file with explanations)

```
# TYPE  DATABASE  USER        ADDRESS            METHOD
local   all       all                            trust           # Unix socket (inside container)
host    all       all         127.0.0.1/32       scram-sha-256   # Loopback IPv4
host    all       all         ::1/128            scram-sha-256   # Loopback IPv6
host    all       all         172.16.0.0/12      scram-sha-256   # Docker bridge networks
host    replication replicator 10.8.0.2/32       scram-sha-256   # Replica replication user via WG
host    all       whydud      10.8.0.2/32        scram-sha-256   # Replica app reads via WG
```

### init.sql (runs once on first volume init)

Creates: TimescaleDB extension, pgcrypto extension, 7 custom schemas (users, email_intel, scoring, tco, community, admin), grants all privileges to `whydud` user.

**CRITICAL:** This only runs when the Docker volume is first created. If the volume already exists (e.g., after a `docker compose up` without `--volumes`), init.sql does NOT re-run. TimescaleDB extension creation is also handled in migration files as a safety net.

### init-replication.sh (runs once on first volume init)

Creates the `replicator` user with `REPLICATION` privilege using `$REPLICATOR_PASSWORD` from the environment.

### Custom Database Schemas

| Schema | Used By |
|---|---|
| public | products, pricing, deals, wishlists, search, scraping, admin_tools, django internals |
| users | accounts (User, Profile, NotificationPreference) |
| email_intel | email_intel (InboundEmail, EmailThread, etc.) |
| scoring | scoring (DudScore, DudScoreHistory, ScoreWeight) |
| tco | tco (TCOCalculation, OwnershipCost) |
| community | discussions, reviews, rewards |
| admin | admin_tools |

Django connects with `search_path=public,users,email_intel,scoring,tco,community,admin` set in prod.py.

### TimescaleDB Migration Pattern

TimescaleDB `create_hypertable()` and continuous aggregates CANNOT run inside any transaction block (including psycopg3's implicit auto-BEGIN). The pattern is:

```python
def _create_hypertable(apps, schema_editor):
    conn = schema_editor.connection
    raw_conn = conn.connection          # underlying psycopg3 connection
    was_autocommit = raw_conn.autocommit
    raw_conn.autocommit = True          # CRITICAL: disable implicit transactions
    try:
        with raw_conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
            cur.execute("CREATE TABLE IF NOT EXISTS ...")
            cur.execute("SELECT create_hypertable(..., if_not_exists => TRUE);")
    finally:
        raw_conn.autocommit = was_autocommit

class Migration(migrations.Migration):
    atomic = False  # Belt-and-suspenders
    operations = [migrations.RunPython(_create_hypertable, ...)]
```

Reference implementations:
- `backend/apps/pricing/migrations/0002_timescaledb_setup.py`
- `backend/apps/scoring/migrations/0002_dudscore_history_hypertable.py`

---

## 14. Caddyfile Configuration

### Full Caddyfile (docker/Caddyfile.cloudflare)

```caddyfile
whydud.com, www.whydud.com {
    tls /etc/caddy/certs/origin.pem /etc/caddy/certs/origin-key.pem

    handle /api/* {
        reverse_proxy backend:8000
    }
    handle /admin/* {
        reverse_proxy backend:8000
    }
    handle /webhooks/* {
        reverse_proxy backend:8000
    }
    handle /accounts/* {
        reverse_proxy backend:8000          # AllAuth social login flows
    }
    handle /oauth/* {
        reverse_proxy backend:8000          # OAuth completion redirect
    }
    handle /static/* {
        reverse_proxy backend:8000          # WhiteNoise serves Django static
    }
    handle {
        reverse_proxy frontend:3000         # Everything else → Next.js
    }

    header {
        X-Frame-Options DENY
        X-Content-Type-Options nosniff
        Referrer-Policy strict-origin-when-cross-origin
        Permissions-Policy "camera=(), microphone=(), geolocation=()"
        -Server
    }

    log {
        output stdout
        format json
    }
}
```

**Key points:**
- Uses Cloudflare Origin Certificate for TLS (mounted from `docker/certs/`)
- Caddy handles both HTTP and HTTPS (redirects 80→443)
- Routes are ordered: specific paths first, catch-all `handle` last
- `backend:8000` and `frontend:3000` are Docker network hostnames
- Security headers applied to all responses
- Server header stripped (`-Server`)

---

## 15. Django Production Settings

### prod.py Key Configuration

| Setting | Value | Why |
|---|---|---|
| `DEBUG` | `False` | Never True in production |
| `ALLOWED_HOSTS` | whydud.com, www.whydud.com, backend, localhost | `backend` for Next.js SSR calls, `localhost` for health checks |
| `USE_X_FORWARDED_HOST` | `True` | Caddy sets X-Forwarded-Host |
| `SECURE_PROXY_SSL_HEADER` | `("HTTP_X_FORWARDED_PROTO", "https")` | Cloudflare sets this |
| `CSRF_TRUSTED_ORIGINS` | https://whydud.com, https://www.whydud.com | Required behind reverse proxy |
| `CORS_ALLOWED_ORIGINS` | https://whydud.com, https://www.whydud.com | Browser API calls |
| `CORS_ALLOW_CREDENTIALS` | `True` | Send cookies with CORS requests |

### Database Configuration in prod.py

```python
# Parse DATABASE_URL from Docker Compose environment
_db_url = os.environ.get("DATABASE_URL")
if _db_url:
    DATABASES["default"] = _parse_db_url(_db_url)

# Optional: write routing for replica node
_write_url = os.environ.get("DATABASE_WRITE_URL")
if _write_url:
    DATABASES["write"] = _parse_db_url(_write_url)
    DATABASE_ROUTERS = ["whydud.db_router.PrimaryReplicaRouter"]
```

The `_parse_db_url()` function parses `postgres://user:pass@host:port/dbname` into Django's `DATABASES` dict format, including `search_path` for custom schemas and `CONN_MAX_AGE=60`.

### Database Router (db_router.py)

- `db_for_read()` → always returns `"default"` (local database)
- `db_for_write()` → returns `"write"` if `DATABASE_WRITE_URL` is set (replica routes writes to primary via WireGuard), otherwise `"default"`
- `allow_migrate()` → only on `"default"` (migrations never run on the write alias)

### WhiteNoise Static Files

WhiteNoiseMiddleware is inserted directly after SecurityMiddleware in the middleware stack. It serves collected static files (Django admin CSS/JS) directly from Gunicorn without needing a separate static file server. Storage backend: `CompressedManifestStaticFilesStorage` (gzip + content hashing).

---

## 16. Troubleshooting

### Issue 1: Django Can't Connect to PostgreSQL

**Symptom:** `connection refused` or `could not connect to server` on backend startup.
**Cause:** `prod.py` originally read individual env vars (`POSTGRES_HOST`, etc.) instead of `DATABASE_URL` set by Docker Compose.
**Fix:** prod.py now parses `DATABASE_URL` via `_parse_db_url()`.
**Prevention:** Always use `DATABASE_URL` pattern — Docker Compose sets it in the service environment.

### Issue 2: 403 Forbidden on All POST Requests

**Symptom:** CSRF verification failed. Request aborted.
**Cause:** Missing `CSRF_TRUSTED_ORIGINS` in Django settings. When behind Cloudflare, the `Origin` header is `https://whydud.com` but Django doesn't know to trust it.
**Fix:** Added `CSRF_TRUSTED_ORIGINS = ["https://whydud.com", "https://www.whydud.com"]` to prod.py.
**Prevention:** Always set `CSRF_TRUSTED_ORIGINS` when Django is behind any reverse proxy.

### Issue 3: Browser API Calls Blocked by CORS

**Symptom:** Console error: `Access to fetch at ... from origin 'https://whydud.com' has been blocked by CORS policy`.
**Cause:** Missing `CORS_ALLOWED_ORIGINS` in Django settings.
**Fix:** Added `CORS_ALLOWED_ORIGINS` + `CORS_ALLOW_CREDENTIALS = True` to prod.py.

### Issue 4: Replica Writes Fail

**Symptom:** Database errors on write operations from replica node.
**Cause:** No database router to redirect writes from replica to primary via WireGuard.
**Fix:** Created `db_router.py` with `PrimaryReplicaRouter`. Activated when `DATABASE_WRITE_URL` is set.

### Issue 5: init-replication.sql Docker Mount Fails

**Symptom:** `docker compose up` fails with "file not found" for init-replication.sql.
**Cause:** The `.sql` file was in `.gitignore` (had a hardcoded password). After `git pull` on server, the file didn't exist.
**Fix:** Replaced with `init-replication.sh` that reads `$REPLICATOR_PASSWORD` from env.
**Prevention:** Never put files in `.gitignore` that Docker Compose mounts.

### Issue 6: /accounts, /oauth, /static Return 404

**Symptom:** Google OAuth redirects fail. Django admin has no CSS.
**Cause:** Caddyfile only had routes for `/api/*`, `/admin/*`, `/webhooks/*`. Missing routes sent these to Next.js which returned 404.
**Fix:** Added `handle /accounts/* { reverse_proxy backend:8000 }`, same for `/oauth/*` and `/static/*`.

### Issue 7: collectstatic Failed Silently

**Symptom:** Django admin loads but has no CSS/JS styling.
**Cause:** Dockerfile had `RUN python manage.py collectstatic || true` — the `|| true` swallowed the error (no SECRET_KEY at build time).
**Fix:** Changed to `RUN DJANGO_SECRET_KEY=build-only-collectstatic-key python manage.py collectstatic --no-input --settings=whydud.settings.prod`.
**Prevention:** Never use `|| true` on critical build steps.

### Issue 8: static_files Volume Shadowing WhiteNoise

**Symptom:** Django admin still has no CSS even after collectstatic fix.
**Cause:** Docker Compose mounted a `static_files` volume at `/app/staticfiles`, overriding the files collected into the Docker image.
**Fix:** Removed `static_files` volume from both compose files. WhiteNoise serves from the image.

### Issue 9: create_hypertable Function Not Found

**Symptom:** `ERROR: function create_hypertable(unknown, unknown) does not exist` during migrations.
**Cause:** TimescaleDB extension wasn't created. `init.sql` (which runs `CREATE EXTENSION timescaledb`) only executes on first Docker volume init. If the volume already existed, init.sql never ran.
**Fix:** Added `CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;` to both TimescaleDB migration files.
**Prevention:** Always create the extension in the migration itself, not just in init.sql.

### Issue 10: TimescaleDB "Must Be Preloaded"

**Symptom:** `ERROR: extension "timescaledb" must be preloaded via shared_preload_libraries`.
**Cause:** `primary.conf` overrode PostgreSQL's default config but was missing `shared_preload_libraries = 'timescaledb'`.
**Fix:** Added `shared_preload_libraries = 'timescaledb'` as the first line in `primary.conf`.
**Restart required:** `docker compose restart postgres` then wait ~20 seconds.

### Issue 11: DisallowedHost 'backend:8000'

**Symptom:** `django.core.exceptions.DisallowedHost: Invalid HTTP_HOST header: 'backend:8000'`. All API data missing from pages.
**Cause:** Next.js server-side rendering calls Django at `http://backend:8000/api/...` (via `INTERNAL_API_URL`). The `Host` header is `backend:8000`, not in `ALLOWED_HOSTS`.
**Fix:** Added `"backend"` and `"localhost"` to `ALLOWED_HOSTS` in prod.py.
**Prevention:** Always include internal Docker hostnames in `ALLOWED_HOSTS`.

### Issue 12: Docker Build Cached After Code Change

**Symptom:** `git pull` shows changes, `docker compose build` shows all "CACHED", containers show "Running" not "Started".
**Cause:** Docker's build cache matched file checksums. And `docker compose up -d` doesn't recreate containers unless the image or config changed.
**Fix:** Use `docker compose build --no-cache backend` and `docker compose up -d --force-recreate backend`.
**Also:** Ensure you actually pushed the code first! `git pull` saying "Already up to date" means the commit wasn't pushed to remote.

### Issue 13: numpy / spacy Binary Incompatibility

**Symptom:** `ImportError` when importing spacy, or `RuntimeError: numpy.dtype size changed`.
**Cause:** numpy 2.x broke binary compatibility with spacy 3.7.5's pre-compiled Cython extensions.
**Fix:** Pin `numpy==1.26.4` in `backend/requirements/base.txt`.
**Warning:** `local-freeze.txt` still has `numpy==2.4.1`. Never install from freeze files.

### Issue 14: Redis Version Conflict

**Symptom:** Celery connection errors or unexpected behavior.
**Cause:** `base.txt` pins `redis==5.2.1` but freeze files have `redis==7.1.0`.
**Fix:** Always install from `base.txt`, not freeze files.

### Issue 15: allauth OAuth Errors

**Symptom:** `ModuleNotFoundError: No module named 'jwt'` or OAuth callback failures.
**Cause:** allauth requires PyJWT for Google OAuth. Newer allauth versions changed internal APIs.
**Fix:** Pinned `django-allauth==65.14.3` and added `PyJWT==2.10.1` to `base.txt`.

### Issue 16: Marketplace Slug Mismatch ("Unknown marketplace: amazon-in")

**Symptom:** Spider tasks fail with `Unknown marketplace: amazon-in`. ScraperJob status shows `failed`.
**Cause:** `seed_marketplaces` management command created slugs with underscores (`amazon_in`) but the entire codebase (spider `MARKETPLACE_SLUG`, Celery Beat args, API URLs) uses hyphens (`amazon-in`).
**Fix:** Updated `seed_marketplaces.py` to use hyphens. Added `_SLUG_MIGRATIONS` dict to auto-fix existing DB records. Re-ran `seed_marketplaces` after rebuilding backend image.
**Prevention:** Always use hyphens in marketplace slugs. Underscores are a Python naming convention, not a URL/slug convention.

### Issue 17: playwright-stealth Missing in Production

**Symptom:** Spider subprocess crashes with `ModuleNotFoundError: No module named 'playwright_stealth'`.
**Cause:** `playwright-stealth==2.0.2` was in `lock.txt` (local dev freeze) but missing from `base.txt` (which the prod Dockerfile installs from).
**Fix:** Added `playwright-stealth==2.0.2` to `backend/requirements/base.txt`.
**Prevention:** Always add new packages to `base.txt`, not just install locally.

### Issue 18: Spider Output Invisible in Container Logs

**Symptom:** `docker compose logs celery-scraping` shows task start/end but no scraping progress details.
**Cause:** All 3 spider tasks used `subprocess.run(capture_output=True)`, silently capturing all stdout/stderr.
**Fix:** Replaced with `subprocess.Popen` + line-by-line streaming via `_run_spider_process()` helper.

### Issue 19: Playwright Chromium Binary Not Found (Non-Root User)

**Symptom:** `playwright._impl._errors.Error: BrowserType.launch: Executable doesn't exist at /home/whydud/.cache/ms-playwright/chromium_headless_shell-1208/...`
**Cause:** `playwright install chromium` runs as root during Docker build `deps` stage → installs to `/root/.cache/ms-playwright/`. Production stage switches to `USER whydud` → runtime looks in `/home/whydud/.cache/ms-playwright/`.
**Fix:** Set `PLAYWRIGHT_BROWSERS_PATH=/ms-playwright` in base ENV (affects both build-time install and runtime lookup). Added `chmod -R o+rx /ms-playwright` after install so non-root user can read/execute the binaries.
**Prevention:** Always use a shared, absolute path for Playwright browsers when running as non-root.

### Issue 20: Running Wrong Compose File on Wrong Node

**Symptom:** Redis fails to bind `10.8.0.1:6379` on replica, containers can't resolve `postgres` hostname, networking chaos.
**Cause:** Accidentally ran `docker compose -f docker-compose.primary.yml` on the replica server. Primary compose binds Redis to `10.8.0.1` (WireGuard IP only available on primary).
**Fix:** Stop all containers, remove orphans (`docker compose down --remove-orphans`), use correct compose file (`docker-compose.replica.yml` on replica).
**Prevention:** Always verify which server you're on before running compose commands. Consider aliasing: `alias dc-primary='docker compose -f docker-compose.primary.yml'` and `alias dc-replica='docker compose -f docker-compose.replica.yml'`.

### Issue 21: Django createsuperuser with Custom User Model

**Symptom:** `createsuperuser --username admin` fails — the User model uses `email` as `USERNAME_FIELD`.
**Fix:** Use shell one-liner instead:
```bash
docker compose -f docker-compose.primary.yml exec backend python -c "
import django; django.setup()
from apps.accounts.models import User
User.objects.create_superuser(email='admin@whydud.com', password='<password>')
"
```

---

## 17. Known Bottlenecks & Improvements

### 1. No .dockerignore File

**Impact:** Docker sends entire build context (including .git/, node_modules/, __pycache__) to daemon. Currently small but will grow.
**Fix:** Create `.dockerignore` with:
```
.git
.github
node_modules
__pycache__
*.pyc
.env*
docker/certs
error logs
docs
*.md
```

### 2. Freeze Files Outdated

**Impact:** `local-freeze.txt` and `lock.txt` have conflicting versions (numpy 2.4.1 vs 1.26.4, redis 7.1.0 vs 5.2.1). Someone installing from freeze files will get broken builds.
**Fix:** Either delete freeze files or regenerate from a clean `pip install -r base.txt -r prod.txt && pip freeze`.

### 3. No CI/CD Pipeline

**Impact:** Every deploy requires manual SSH → git pull → build → restart. Error-prone, slow.
**Fix:** GitHub Actions workflow: push to master → build images → push to registry → SSH deploy.

### 4. Database Backups Not Verified

**Impact:** `/opt/scripts/backup-db.sh` exists but cron jobs haven't been verified as running.
**Fix:** Verify cron entries, test restore procedure, set up off-site backup (S3/Backblaze).

### 5. No Health Check Endpoint

**Impact:** No way to programmatically verify backend is healthy beyond curl to /api/v1/products/.
**Fix:** Add `/api/v1/health/` endpoint returning DB status, Redis status, Meilisearch status.

### 6. Sentry Not Configured

**Impact:** `sentry-sdk[django]` is installed and `SENTRY_DSN` env var exists, but it's empty. No error tracking.
**Fix:** Create Sentry project, set `SENTRY_DSN` in .env, configure in base.py.

### 7. ~~Replica Node Not Deployed~~ RESOLVED

**Status:** Completed 2026-03-03. Replica running at 46.250.237.93 with 7 containers (postgres replica, redis, meilisearch, backend, frontend, celery-scraping, caddy).

### 8. ~~PostgreSQL Replication Not Set Up~~ RESOLVED

**Status:** Completed 2026-03-03. Streaming replication active, WAL positions match, replication slot `replica_slot` active.

### 9. ~~WireGuard Tunnel Unverified~~ RESOLVED

**Status:** Verified 2026-03-03. Bidirectional connectivity confirmed (10.8.0.1 ↔ 10.8.0.2). Replica connects to primary PostgreSQL and Redis over WireGuard.

### 10. No Rollback Strategy

**Impact:** If a deploy breaks production, there's no quick way to roll back.
**Fix:** Tag releases, keep previous Docker image, document rollback commands:
```bash
git checkout <previous-commit>
docker compose build
docker compose up -d --force-recreate
```

### 11. No Docker Image Registry

**Impact:** Images are built directly on the server. Build failures = broken deploy. Slow on low-CPU servers.
**Fix:** Push images to Docker Hub or GitHub Container Registry. Pull pre-built images on server.

### 12. No CDN for Static Assets

**Impact:** WhiteNoise serves Django static files from Gunicorn. Next.js static assets served from container. No edge caching.
**Fix:** Configure Cloudflare to cache `/static/*` and `/_next/static/*` with long TTLs.

### 13. No Load Testing

**Impact:** Unknown capacity limits. Don't know when to scale.
**Fix:** Run `k6` or `locust` load tests against staging.

### 14. No Persistent Caddy Logs

**Impact:** Caddy logs to stdout only. Docker log rotation may lose data.
**Fix:** Mount a log volume or ship to a log aggregator (Loki, Elasticsearch).

### 15. No Connection Pooling

**Impact:** Direct PostgreSQL connections (`max_connections=100`). Under load, connection storms can exhaust the pool.
**Fix:** Add PgBouncer between Django and PostgreSQL.

---

## 18. Useful Commands Reference

### Docker Compose (prefix with `docker compose -f docker-compose.primary.yml`)

```bash
# View all containers
docker compose -f docker-compose.primary.yml ps

# View logs (all services)
docker compose -f docker-compose.primary.yml logs -f

# View logs (specific service, last 100 lines)
docker compose -f docker-compose.primary.yml logs backend --tail=100
docker compose -f docker-compose.primary.yml logs caddy --tail=50
docker compose -f docker-compose.primary.yml logs frontend --tail=50

# Restart a service
docker compose -f docker-compose.primary.yml restart backend

# Rebuild and restart
docker compose -f docker-compose.primary.yml build backend
docker compose -f docker-compose.primary.yml up -d --force-recreate backend

# Force rebuild (no cache)
docker compose -f docker-compose.primary.yml build --no-cache backend

# Stop everything
docker compose -f docker-compose.primary.yml down

# Stop and remove volumes (DESTRUCTIVE — deletes data)
docker compose -f docker-compose.primary.yml down -v
```

### Database Access

```bash
# Django shell
docker compose -f docker-compose.primary.yml exec backend python manage.py shell

# psql into PostgreSQL
docker compose -f docker-compose.primary.yml exec postgres psql -U whydud -d whydud

# Run a SQL query
docker compose -f docker-compose.primary.yml exec postgres psql -U whydud -d whydud -c "SELECT count(*) FROM products_product;"

# Check database size
docker compose -f docker-compose.primary.yml exec postgres psql -U whydud -d whydud -c "SELECT pg_size_pretty(pg_database_size('whydud'));"
```

### Migrations

```bash
# Run all pending migrations
docker compose -f docker-compose.primary.yml run --rm backend python manage.py migrate --no-input

# Show migration status
docker compose -f docker-compose.primary.yml run --rm backend python manage.py showmigrations

# Show SQL for a specific migration
docker compose -f docker-compose.primary.yml run --rm backend python manage.py sqlmigrate pricing 0001

# Make new migrations (after model changes)
docker compose -f docker-compose.primary.yml run --rm backend python manage.py makemigrations
```

### Celery

```bash
# Check active tasks
docker compose -f docker-compose.primary.yml exec celery-worker celery -A whydud inspect active

# Check scheduled tasks
docker compose -f docker-compose.primary.yml exec celery-worker celery -A whydud inspect scheduled

# Purge all pending tasks (CAREFUL)
docker compose -f docker-compose.primary.yml exec celery-worker celery -A whydud purge

# Run a task manually
docker compose -f docker-compose.primary.yml exec backend python manage.py shell -c "
from apps.scraping.tasks import run_marketplace_spider
run_marketplace_spider.delay('amazon-in')
"
```

### Backup & Restore

```bash
# Backup database
docker compose -f docker-compose.primary.yml exec postgres pg_dump -U whydud -d whydud -Fc > /opt/backups/postgres/whydud_$(date +%Y%m%d).dump

# Restore database (DESTRUCTIVE — overwrites current data)
docker compose -f docker-compose.primary.yml exec -T postgres pg_restore -U whydud -d whydud --clean --if-exists < /opt/backups/postgres/whydud_20260303.dump
```

### Health Checks

```bash
# Backend API
docker compose -f docker-compose.primary.yml exec backend curl -sf http://localhost:8000/api/v1/products/

# Frontend
docker compose -f docker-compose.primary.yml exec caddy curl -sf http://frontend:3000/

# PostgreSQL
docker compose -f docker-compose.primary.yml exec postgres pg_isready -U whydud -d whydud

# Redis
docker compose -f docker-compose.primary.yml exec redis redis-cli -a $REDIS_PASSWORD ping

# Meilisearch
docker compose -f docker-compose.primary.yml exec meilisearch curl -sf http://localhost:7700/health

# All at once (external)
curl -v https://whydud.com
curl -v https://whydud.com/api/v1/products/
```

### Replication (after setup)

```bash
# Check replication status (on primary)
docker compose -f docker-compose.primary.yml exec postgres psql -U whydud -d whydud -c "SELECT * FROM pg_stat_replication;"

# Check replication slots
docker compose -f docker-compose.primary.yml exec postgres psql -U whydud -d whydud -c "SELECT slot_name, active FROM pg_replication_slots;"

# Check if this node is a replica
docker compose -f docker-compose.replica.yml exec postgres psql -U whydud -d whydud -c "SELECT pg_is_in_recovery();"

# Check replication lag
docker compose -f docker-compose.replica.yml exec postgres psql -U whydud -d whydud -c "SELECT now() - pg_last_xact_replay_timestamp() AS replication_lag;"
```

### Debugging

```bash
# Check Django settings
docker compose -f docker-compose.primary.yml exec backend python manage.py shell -c "
from django.conf import settings
print('ALLOWED_HOSTS:', settings.ALLOWED_HOSTS)
print('DATABASES:', {k: {j: v for j, v in db.items() if j != 'PASSWORD'} for k, db in settings.DATABASES.items()})
print('INSTALLED_APPS:', settings.INSTALLED_APPS)
"

# Check environment variables in a container
docker compose -f docker-compose.primary.yml exec backend env | sort

# Check disk space
df -h
docker system df

# Clean up unused Docker resources
docker system prune -f
docker image prune -a -f
```
