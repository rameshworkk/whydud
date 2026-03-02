# Whydud Production Infrastructure Architecture
# Last updated: 2026-03-02
# Purpose: Reference document for Claude Code and deployment operations

## Overview

Whydud runs on a **two-node active-active** architecture with PostgreSQL streaming replication, WireGuard VPN tunnel, and Cloudflare load balancing.

---

## Servers

### Node 1: PRIMARY (whydud-primary)
- **Provider:** Contabo VPS
- **Public IP:** 95.111.232.70
- **WireGuard IP:** 10.0.0.1
- **Specs:** 12 GB RAM / 6 vCPU
- **OS:** Ubuntu 24
- **Hostname:** whydud-primary
- **Role:** PostgreSQL PRIMARY, Celery Beat (scheduler), general Celery worker, full web stack
- **SSH:** `ssh -i C:\Users\rames\Downloads\whydud-key deploy@95.111.232.70`

### Node 2: REPLICA (whydud-replica)
- **Provider:** Contabo VPS
- **Public IP:** 46.250.237.93
- **WireGuard IP:** 10.0.0.2
- **Specs:** 8 GB RAM / 4 vCPU
- **OS:** Ubuntu 24
- **Hostname:** whydud-replica
- **Role:** PostgreSQL REPLICA (streaming), scraping Celery worker, full web stack
- **SSH:** `ssh -i C:\Users\rames\Downloads\whydud-key deploy@46.250.237.93`

---

## Network Architecture

```
                    Internet
                       │
              ┌────────┴────────┐
              │   Cloudflare    │
              │  DNS + CDN +    │
              │  SSL + LB      │
              │  (whydud.com)  │
              └───┬────────┬───┘
                  │        │
          ┌───────┴──┐  ┌──┴───────┐
          │ A Record │  │ A Record │
          │95.111.   │  │46.250.   │
          │232.70    │  │237.93    │
          └────┬─────┘  └────┬─────┘
               │             │
    ┌──────────┴──┐    ┌─────┴──────────┐
    │  PRIMARY    │    │   REPLICA       │
    │  :80 Caddy  │    │   :80 Caddy    │
    │  :5432 PG   │◄──►│   :5432 PG     │
    │  :6379 Redis│    │   :6379 Redis  │
    │  :7700 Meili│    │   :7700 Meili  │
    └─────────────┘    └────────────────┘
          │                    │
          └──── WireGuard ─────┘
               10.0.0.1 ↔ 10.0.0.2
               UDP 51820
```

### Cloudflare Configuration
- **Domain:** whydud.com
- **DNS Records:**
  - A @ → 95.111.232.70 (Proxied) — primary
  - A @ → 46.250.237.93 (Proxied) — replica
  - A www → 95.111.232.70 (Proxied)
  - A www → 46.250.237.93 (Proxied)
  - MX records → Zoho Mail (mx.zoho.com, mx2.zoho.com, mx3.zoho.com)
- **SSL:** Full (strict) — Cloudflare terminates SSL, Caddy serves HTTP internally
- **Load Balancing:** Round-robin via dual A records (free, automatic)

### WireGuard VPN
- **Primary:** 10.0.0.1/24 (ListenPort 51820)
- **Replica:** 10.0.0.2/24 (ListenPort 51820)
- **Config location:** /etc/wireguard/wg0.conf
- **Monitor:** /opt/scripts/wg-monitor.sh (cron every 5 min)
- **Purpose:** Secure inter-node communication for PostgreSQL replication, Redis shared broker, database write routing

### Firewall (UFW on both nodes)
- 22/tcp — SSH
- 80/tcp — HTTP (Caddy)
- 443/tcp — HTTPS (Caddy)
- 51820/udp — WireGuard

---

## Directory Structure (both nodes)

```
/opt/whydud/                    # Project root
├── .env                        # Environment variables (symlinked into whydud/)
└── whydud/                     # Git repo (cloned from GitHub)
    ├── backend/                # Django app
    │   ├── apps/               # Django apps (accounts, scraping, scoring, etc.)
    │   ├── whydud/             # Django settings, wsgi, celery
    │   └── requirements/       # base.txt, prod.txt, dev.txt
    ├── frontend/               # Next.js app
    │   ├── src/
    │   └── package.json
    ├── docker/
    │   ├── Dockerfiles/
    │   │   ├── backend.Dockerfile
    │   │   └── frontend.Dockerfile
    │   ├── Caddyfile.cloudflare    # Caddy config for behind-Cloudflare
    │   └── postgres/
    │       ├── init.sql            # Schema init (TimescaleDB, schemas, grants)
    │       ├── primary.conf        # PostgreSQL primary config (PRIMARY only)
    │       ├── pg_hba.conf         # PostgreSQL HBA rules (PRIMARY only)
    │       └── init-replication.sql # Creates replicator user (PRIMARY only)
    ├── docker-compose.primary.yml  # PRIMARY node compose
    ├── docker-compose.replica.yml  # REPLICA node compose
    └── docs/

/opt/scripts/                   # Operational scripts
├── backup-db.sh                # Daily DB backup (3 AM cron)
├── docker-cleanup.sh           # Weekly Docker prune (Sunday 4 AM)
└── wg-monitor.sh               # WireGuard tunnel health check (every 5 min)

/opt/backups/postgres/          # DB backups (7-day retention)
```

---

## Services per Node

### PRIMARY (docker-compose.primary.yml)

| Service | Image/Build | Port | Memory Limit | Notes |
|---------|------------|------|-------------|-------|
| postgres | timescale/timescaledb:latest-pg16 | 127.0.0.1:5432, 10.0.0.1:5432 | 3G | PRIMARY with streaming replication |
| redis | redis:7-alpine | 127.0.0.1:6379, 10.0.0.1:6379 | 768M | Shared broker (replica connects via WireGuard) |
| meilisearch | getmeili/meilisearch:v1.7 | 127.0.0.1:7700 | 1G | Product search engine |
| caddy | caddy:2-alpine | 80, 443 | 128M | Reverse proxy (HTTP only behind Cloudflare) |
| backend | backend.Dockerfile (production) | internal:8000 | 2G | Django + Gunicorn (3 workers, gthread) |
| frontend | frontend.Dockerfile (production) | internal:3000 | 1G | Next.js SSR |
| celery-worker | backend.Dockerfile | — | 1G | Queues: default, scoring, alerts, email |
| celery-beat | backend.Dockerfile | — | 256M | Scheduler (only runs on PRIMARY) |

### REPLICA (docker-compose.replica.yml)

| Service | Image/Build | Port | Memory Limit | Notes |
|---------|------------|------|-------------|-------|
| postgres | timescale/timescaledb:latest-pg16 | 127.0.0.1:5432 | 2G | REPLICA (streaming from primary) |
| redis | redis:7-alpine | 127.0.0.1:6379 | 512M | Local cache only |
| meilisearch | getmeili/meilisearch:v1.7 | 127.0.0.1:7700 | 1G | Product search engine |
| caddy | caddy:2-alpine | 80, 443 | 128M | Reverse proxy |
| backend | backend.Dockerfile (production) | internal:8000 | 1536M | Django + Gunicorn (2 workers, gthread) |
| frontend | frontend.Dockerfile (production) | internal:3000 | 1G | Next.js SSR |
| celery-scraping | backend.Dockerfile | — | 2G | Queues: scraping only |

---

## Database Architecture

### PostgreSQL Streaming Replication
- **Primary (10.0.0.1:5432):** Accepts all reads and writes
- **Replica (10.0.0.2:5432):** Read-only replica, streams WAL from primary
- **Replication user:** `replicator` (created by init-replication.sql)
- **Replication slot:** `replica_slot`

### Write Routing (Django)
- PRIMARY node: All reads/writes go to local postgres (DATABASE_URL)
- REPLICA node: Reads go to local postgres (DATABASE_URL), writes routed to primary via WireGuard (DATABASE_WRITE_URL = postgres://...@10.0.0.1:5432/whydud)
- Implemented via Django database router class

### Primary PostgreSQL Config (primary.conf)
```
wal_level = replica
max_wal_senders = 5
wal_keep_size = 1GB
shared_buffers = 1GB
effective_cache_size = 3GB
work_mem = 32MB
maintenance_work_mem = 256MB
max_connections = 100
listen_addresses = *
```

### pg_hba.conf (Primary only)
```
local   all             all                                     trust
host    all             all             127.0.0.1/32            scram-sha-256
host    all             all             ::1/128                 scram-sha-256
host    all             all             172.16.0.0/12           scram-sha-256
host    replication     replicator      10.0.0.2/32             scram-sha-256
host    all             whydud          10.0.0.2/32             scram-sha-256
```

### Database Extensions
- TimescaleDB (hypertables for price_snapshots, dudscore_history)
- pgcrypto (UUID generation)

### Schemas
- public, users, email_intel, scoring, tco, community, admin

---

## Redis Architecture
- **Primary (10.0.0.1:6379):** Shared Celery broker + cache + sessions
- **Replica (local 6379):** Local cache only
- **Replica's Celery broker:** Points to primary Redis via WireGuard (10.0.0.1:6379)
- **Auth:** Password protected (REDIS_PASSWORD env var)

---

## Caddy (Reverse Proxy)

Behind Cloudflare, Caddy listens on port 80 only (HTTP). Cloudflare handles SSL.

**Routing:**
- `/api/*` → backend:8000 (Django)
- `/admin/*` → backend:8000 (Django)
- `/webhooks/*` → backend:8000 (Django)
- `/*` → frontend:3000 (Next.js)

---

## Environment Variables

### Shared (both nodes)
```
DJANGO_SETTINGS_MODULE=whydud.settings.prod
DJANGO_SECRET_KEY=<secret>
DJANGO_ALLOWED_HOSTS=whydud.com,www.whydud.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://whydud.com,https://www.whydud.com
POSTGRES_USER=whydud
POSTGRES_PASSWORD=<secret>
POSTGRES_DB=whydud
REDIS_PASSWORD=<secret>
MEILISEARCH_MASTER_KEY=<secret>
EMAIL_ENCRYPTION_KEY=<secret>
OAUTH_ENCRYPTION_KEY=<secret>
NEXT_PUBLIC_API_URL=https://whydud.com/api
NEXT_PUBLIC_SITE_URL=https://whydud.com
```

### Primary only
```
NODE_ROLE=primary
DATABASE_URL=postgres://whydud:<pass>@postgres:5432/whydud
REDIS_URL=redis://:<pass>@redis:6379/0
CELERY_BROKER_URL=redis://:<pass>@redis:6379/0
```

### Replica only
```
NODE_ROLE=replica
DATABASE_URL=postgres://whydud:<pass>@postgres:5432/whydud          # local replica (reads)
DATABASE_WRITE_URL=postgres://whydud:<pass>@10.0.0.1:5432/whydud    # primary via WireGuard (writes)
REDIS_URL=redis://:<pass>@redis:6379/0                              # local redis
CELERY_BROKER_URL=redis://:<pass>@10.0.0.1:6379/0                  # primary redis via WireGuard
CELERY_RESULT_BACKEND=redis://:<pass>@10.0.0.1:6379/1
SCRAPING_PROXY_LIST=http://<dataimpulse_credentials>@gw.dataimpulse.com:823
SCRAPING_PROXY_TYPE=rotating
```

---

## Deployment Commands

### Pull and deploy new code (both nodes)
```bash
cd /opt/whydud/whydud
git pull origin master
docker compose -f docker-compose.<primary|replica>.yml build
docker compose -f docker-compose.<primary|replica>.yml up -d
```

### Start/Stop services
```bash
# Primary
docker compose -f docker-compose.primary.yml up -d
docker compose -f docker-compose.primary.yml down

# Replica
docker compose -f docker-compose.replica.yml up -d
docker compose -f docker-compose.replica.yml down
```

### Run Django migrations (PRIMARY only)
```bash
docker compose -f docker-compose.primary.yml exec backend python manage.py migrate
```

### Create superuser (PRIMARY only)
```bash
docker compose -f docker-compose.primary.yml exec backend python manage.py createsuperuser
```

### Check replication status (PRIMARY)
```bash
docker exec whydud-postgres psql -U whydud -c \
  "SELECT client_addr, state, pg_wal_lsn_diff(sent_lsn, replay_lsn) AS lag_bytes FROM pg_stat_replication;"
```

### View logs
```bash
docker compose -f docker-compose.<primary|replica>.yml logs -f <service>
# Examples: postgres, backend, frontend, celery-worker, celery-beat, celery-scraping
```

### Manual backup
```bash
/opt/scripts/backup-db.sh
```

### Run scraping (REPLICA only)
```bash
docker compose -f docker-compose.replica.yml exec celery-scraping \
  python -m apps.scraping.runner amazon_in --max-pages 1
```

---

## PostgreSQL Replication Setup (one-time)

### On PRIMARY — after first start
```bash
# Create replication slot (if not auto-created by init-replication.sql)
docker exec whydud-postgres psql -U whydud -c \
  "SELECT pg_create_physical_replication_slot('replica_slot');"
```

### On REPLICA — bootstrap from primary
```bash
# Stop replica postgres
docker compose -f docker-compose.replica.yml stop postgres

# Remove replica data volume
docker volume rm whydud_postgres_data

# Run pg_basebackup from primary via WireGuard
docker run --rm -v whydud_postgres_data:/var/lib/postgresql/data \
  timescale/timescaledb:latest-pg16 \
  pg_basebackup -h 10.0.0.1 -U replicator -D /var/lib/postgresql/data \
  -Fp -Xs -P -R -S replica_slot

# Start replica
docker compose -f docker-compose.replica.yml up -d postgres
```

---

## Failover Procedures

### If PRIMARY dies
```bash
# On REPLICA — promote to primary
docker exec whydud-postgres pg_ctl promote -D /var/lib/postgresql/data

# Update .env: remove DATABASE_WRITE_URL, change NODE_ROLE=primary
# Restart Django
docker compose -f docker-compose.replica.yml up -d backend

# In Cloudflare: remove dead PRIMARY A record
```

### If REPLICA dies
- Primary continues serving all traffic alone
- Scraping pauses (runs on replica)
- Remove replica A record from Cloudflare
- When back: re-bootstrap with pg_basebackup

### Restore after failure
1. Stop all services on failed node
2. Wipe postgres data volume
3. pg_basebackup from current primary
4. Start as replica
5. When caught up, optionally switchover back

---

## Security

- **SSH:** Key-only auth (ed25519), password auth disabled, root login disabled
- **SSH key:** `C:\Users\rames\Downloads\whydud-key` (private), user: `deploy`
- **Fail2ban:** SSH brute force protection, 24h ban after 3 failures
- **PostgreSQL:** Binds to WireGuard IP only (10.0.0.x), never public internet
- **Redis:** Password auth required
- **UFW:** Only ports 22, 80, 443, 51820 open
- **Docker:** Log rotation (10MB max, 3 files)
- **Backups:** Daily at 3 AM, 7-day retention in /opt/backups/postgres/

---

## Systemd Service (auto-start on reboot)

Both nodes have `/etc/systemd/system/whydud.service`:
- Starts after Docker + WireGuard
- Runs `docker compose up -d` with the appropriate compose file
- Managed as `deploy` user

```bash
# Check status
systemctl status whydud

# Manual control
sudo systemctl start whydud
sudo systemctl stop whydud
sudo systemctl restart whydud
```

---

## Cron Jobs (deploy user, both nodes)

| Schedule | Script | Purpose |
|----------|--------|---------|
| 0 3 * * * | /opt/scripts/backup-db.sh | Daily DB backup |
| 0 4 * * 0 | /opt/scripts/docker-cleanup.sh | Weekly Docker prune |
| */5 * * * * | /opt/scripts/wg-monitor.sh | WireGuard tunnel health |

---

## Git Repository

- **Remote:** git@github.com:rameshworkk/whydud.git
- **Branch:** master
- **Deploy keys:** Separate ed25519 keys on each node (~deploy/.ssh/github_key)
- **Clone location:** /opt/whydud/whydud/

---

## Tech Stack Summary

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15.1 (SSR, standalone output) |
| Backend | Django + Gunicorn (gthread workers) |
| Task Queue | Celery + Redis broker |
| Scheduler | Celery Beat (django_celery_beat) |
| Database | PostgreSQL 16 + TimescaleDB |
| Search | Meilisearch v1.7 |
| Cache/Sessions | Redis 7 |
| Reverse Proxy | Caddy 2 |
| CDN/SSL/LB | Cloudflare (free plan) |
| VPN | WireGuard |
| Containers | Docker + Docker Compose |
| Scraping | Scrapy + Playwright + DataImpulse rotating proxy |
| OS | Ubuntu 24 |
