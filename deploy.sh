#!/bin/bash
# ============================================================
# Whydud — Production Deployment Script
# Usage: ./deploy.sh [primary|replica] [--first-run]
# ============================================================
set -euo pipefail

NODE_TYPE="${1:-}"
FIRST_RUN="${2:-}"

if [[ "$NODE_TYPE" != "primary" && "$NODE_TYPE" != "replica" ]]; then
  echo "Usage: ./deploy.sh [primary|replica] [--first-run]"
  echo ""
  echo "  primary    Deploy to PRIMARY node (PostgreSQL primary, Celery Beat)"
  echo "  replica    Deploy to REPLICA node (PostgreSQL replica, scraping worker)"
  echo "  --first-run  First-time setup: run migrations, create superuser, seed"
  exit 1
fi

COMPOSE_FILE="docker-compose.${NODE_TYPE}.yml"
PROJECT_DIR="/opt/whydud/whydud"
ENV_FILE="/opt/whydud/.env"

echo "=== Whydud Deploy: ${NODE_TYPE} node ==="
echo "Compose file: ${COMPOSE_FILE}"
echo ""

# ---- Pre-flight checks ----
if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: $ENV_FILE not found!"
  echo "Copy .env.example to $ENV_FILE and fill in production values."
  exit 1
fi

if ! command -v docker &> /dev/null; then
  echo "ERROR: Docker not installed!"
  exit 1
fi

if ! docker info &> /dev/null; then
  echo "ERROR: Docker daemon not running!"
  exit 1
fi

# ---- Pull latest code ----
echo ">>> Pulling latest code from GitHub..."
cd "$PROJECT_DIR"
git pull origin master

# ---- Build images ----
echo ""
echo ">>> Building Docker images (this may take a few minutes)..."
docker compose -f "$COMPOSE_FILE" build

# ---- Stop existing services (if running) ----
echo ""
echo ">>> Stopping existing services..."
docker compose -f "$COMPOSE_FILE" down --remove-orphans || true

# ---- Start infrastructure services first ----
echo ""
echo ">>> Starting infrastructure (postgres, redis, meilisearch)..."
docker compose -f "$COMPOSE_FILE" up -d postgres redis meilisearch

echo ">>> Waiting for postgres to be healthy..."
for i in $(seq 1 30); do
  if docker compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -U whydud -d whydud > /dev/null 2>&1; then
    echo "    Postgres is ready."
    break
  fi
  if [ "$i" -eq 30 ]; then
    echo "ERROR: Postgres failed to start within 30 attempts!"
    docker compose -f "$COMPOSE_FILE" logs postgres
    exit 1
  fi
  sleep 2
done

echo ">>> Waiting for redis to be healthy..."
for i in $(seq 1 15); do
  if docker compose -f "$COMPOSE_FILE" exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo "    Redis is ready."
    break
  fi
  sleep 2
done

# ---- First-run tasks (PRIMARY only) ----
if [[ "$FIRST_RUN" == "--first-run" && "$NODE_TYPE" == "primary" ]]; then
  echo ""
  echo ">>> Running Django migrations..."
  docker compose -f "$COMPOSE_FILE" run --rm backend python manage.py migrate --no-input

  echo ""
  echo ">>> Creating superuser (follow the prompts)..."
  docker compose -f "$COMPOSE_FILE" run --rm backend python manage.py createsuperuser || true

  echo ""
  echo ">>> Seeding initial data..."
  docker compose -f "$COMPOSE_FILE" run --rm backend python manage.py seed_data || true
fi

# ---- Run migrations on subsequent deploys (PRIMARY only) ----
if [[ "$FIRST_RUN" != "--first-run" && "$NODE_TYPE" == "primary" ]]; then
  echo ""
  echo ">>> Running Django migrations..."
  docker compose -f "$COMPOSE_FILE" run --rm backend python manage.py migrate --no-input
fi

# ---- Start all services ----
echo ""
echo ">>> Starting all services..."
docker compose -f "$COMPOSE_FILE" up -d

# ---- Health check ----
echo ""
echo ">>> Waiting 15 seconds for services to stabilize..."
sleep 15

echo ""
echo ">>> Service status:"
docker compose -f "$COMPOSE_FILE" ps

# Check if backend is responding
echo ""
echo ">>> Checking backend health..."
if docker compose -f "$COMPOSE_FILE" exec -T backend curl -sf http://localhost:8000/api/v1/products/ > /dev/null 2>&1; then
  echo "    Backend is responding."
else
  echo "    WARNING: Backend may not be ready yet. Check logs:"
  echo "    docker compose -f $COMPOSE_FILE logs backend"
fi

echo ""
echo "=== Deploy complete: ${NODE_TYPE} node ==="
echo ""
echo "Useful commands:"
echo "  Logs:        docker compose -f $COMPOSE_FILE logs -f <service>"
echo "  Status:      docker compose -f $COMPOSE_FILE ps"
echo "  Restart:     docker compose -f $COMPOSE_FILE restart <service>"
echo "  Migrations:  docker compose -f $COMPOSE_FILE exec backend python manage.py migrate"
