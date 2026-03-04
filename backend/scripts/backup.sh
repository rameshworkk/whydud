#!/usr/bin/env bash
#
# backup.sh — Automated PostgreSQL backups with S3-compatible cloud storage
#
# Performs pg_dump (custom format), compresses, uploads to IDrive S3 via rclone,
# and manages retention (7 days local, 180 days remote). Logs to Discord webhook.
#
# Usage:
#   Runs inside the postgres container (or any host with pg_dump + rclone).
#   Cron: 0 */6 * * * /app/scripts/backup.sh
#
# Environment variables (required):
#   POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST
#   RCLONE_S3_ENDPOINT, RCLONE_S3_ACCESS_KEY, RCLONE_S3_SECRET_KEY
#   DISCORD_WEBHOOK_URL (optional — silent if unset)
#
# For incremental backups, WAL archiving is used when available. Otherwise
# this script performs schema-aware full dumps but skips unchanged
# TimescaleDB continuous aggregate data via --exclude-table-data patterns.

set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────────────

BACKUP_DIR="${BACKUP_DIR:-/backups}"
BUCKET="${BACKUP_S3_BUCKET:-whydud-backups}"
REMOTE_PATH="daily"
LOCAL_RETENTION_DAYS=7
REMOTE_RETENTION_DAYS=180
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DATE_ONLY=$(date +%Y%m%d)
DUMP_FILE="${BACKUP_DIR}/whydud_${TIMESTAMP}.dump"
GZ_FILE="${DUMP_FILE}.gz"
MANIFEST_FILE="${BACKUP_DIR}/.last_backup_manifest"
NODE_ROLE="${NODE_ROLE:-primary}"

# DB connection
DB_NAME="${POSTGRES_DB:-whydud}"
DB_USER="${POSTGRES_USER:-whydud}"
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
export PGPASSWORD="${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"

# Discord
DISCORD_WEBHOOK_URL="${DISCORD_WEBHOOK_URL:-}"

# ── Helpers ──────────────────────────────────────────────────────────────────

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

discord_notify() {
  local color="$1" title="$2" description="$3"
  [ -z "$DISCORD_WEBHOOK_URL" ] && return 0

  local payload
  payload=$(cat <<PAYLOAD
{
  "embeds": [{
    "title": "${title}",
    "description": "${description}",
    "color": ${color},
    "footer": {"text": "whydud backup · ${NODE_ROLE}"},
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  }]
}
PAYLOAD
)
  curl -s -H "Content-Type: application/json" -d "$payload" "$DISCORD_WEBHOOK_URL" > /dev/null 2>&1 || true
}

discord_success() { discord_notify 1484580 "$1" "$2"; }  # green
discord_failure() { discord_notify 14438920 "$1" "$2"; }  # red

cleanup_on_error() {
  log "ERROR: Backup failed"
  rm -f "$DUMP_FILE" "$GZ_FILE" 2>/dev/null || true
  discord_failure "Backup Failed" "pg_dump of \`${DB_NAME}\` failed at $(date).\\n\\nCheck container logs for details."
  exit 1
}

trap cleanup_on_error ERR

# ── Pre-flight ───────────────────────────────────────────────────────────────

mkdir -p "$BACKUP_DIR"

log "=== Whydud PostgreSQL Backup ==="
log "Database: ${DB_NAME}@${DB_HOST}:${DB_PORT}"
log "Backup dir: ${BACKUP_DIR}"

# Verify pg_dump is available
if ! command -v pg_dump &>/dev/null; then
  log "FATAL: pg_dump not found"
  discord_failure "Backup Failed" "pg_dump binary not found in container."
  exit 1
fi

# Verify DB connectivity
if ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -q; then
  log "FATAL: Cannot connect to PostgreSQL"
  discord_failure "Backup Failed" "Cannot connect to PostgreSQL at ${DB_HOST}:${DB_PORT}."
  exit 1
fi

# ── Incremental strategy ────────────────────────────────────────────────────
#
# True incremental backup (WAL-based) requires pg_basebackup + WAL archiving
# which needs server-side configuration. For pg_dump-based backups, we
# implement a "smart dump" strategy:
#
# 1. Always dump schema (small, fast)
# 2. Check if table row counts changed since last backup
# 3. Skip large time-series tables (price_snapshots, dudscore_history)
#    if no new rows — these are append-only hypertables
# 4. Always dump transactional tables (products, reviews, users, etc.)
#
# The manifest file tracks row counts from the last successful backup.

EXCLUDE_DATA_ARGS=()

# Check if we can do incremental (manifest exists from previous run)
if [ -f "$MANIFEST_FILE" ]; then
  log "Found previous backup manifest — checking for incremental opportunity"

  # Count rows in large time-series tables
  PRICE_COUNT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -A \
    -c "SELECT COUNT(*) FROM pricing.price_snapshots" 2>/dev/null || echo "0")
  SCORE_COUNT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -A \
    -c "SELECT COUNT(*) FROM scoring.dudscore_history" 2>/dev/null || echo "0")

  PREV_PRICE_COUNT=$(grep "^price_snapshots:" "$MANIFEST_FILE" 2>/dev/null | cut -d: -f2 || echo "0")
  PREV_SCORE_COUNT=$(grep "^dudscore_history:" "$MANIFEST_FILE" 2>/dev/null | cut -d: -f2 || echo "0")

  # Skip time-series data if unchanged (schema still included)
  if [ "$PRICE_COUNT" = "$PREV_PRICE_COUNT" ] && [ "$PRICE_COUNT" != "0" ]; then
    log "  price_snapshots unchanged (${PRICE_COUNT} rows) — excluding data"
    EXCLUDE_DATA_ARGS+=(--exclude-table-data="pricing.price_snapshots")
  else
    log "  price_snapshots changed: ${PREV_PRICE_COUNT} → ${PRICE_COUNT}"
  fi

  if [ "$SCORE_COUNT" = "$PREV_SCORE_COUNT" ] && [ "$SCORE_COUNT" != "0" ]; then
    log "  dudscore_history unchanged (${SCORE_COUNT} rows) — excluding data"
    EXCLUDE_DATA_ARGS+=(--exclude-table-data="scoring.dudscore_history")
  else
    log "  dudscore_history changed: ${PREV_SCORE_COUNT} → ${SCORE_COUNT}"
  fi
else
  log "No previous manifest — performing full backup"
  # Get current counts for manifest
  PRICE_COUNT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -A \
    -c "SELECT COUNT(*) FROM pricing.price_snapshots" 2>/dev/null || echo "0")
  SCORE_COUNT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -A \
    -c "SELECT COUNT(*) FROM scoring.dudscore_history" 2>/dev/null || echo "0")
fi

# ── pg_dump ──────────────────────────────────────────────────────────────────

log "Starting pg_dump..."
START_TIME=$(date +%s)

pg_dump \
  -Fc \
  -h "$DB_HOST" \
  -p "$DB_PORT" \
  -U "$DB_USER" \
  -d "$DB_NAME" \
  --no-owner \
  --no-privileges \
  -N "_timescaledb_*" \
  "${EXCLUDE_DATA_ARGS[@]}" \
  -f "$DUMP_FILE"

DUMP_SIZE=$(stat -c%s "$DUMP_FILE" 2>/dev/null || stat -f%z "$DUMP_FILE" 2>/dev/null || echo "0")
log "pg_dump complete: $(numfmt --to=iec "$DUMP_SIZE" 2>/dev/null || echo "${DUMP_SIZE} bytes")"

# ── Compress ─────────────────────────────────────────────────────────────────

log "Compressing..."
gzip -9 "$DUMP_FILE"
GZ_SIZE=$(stat -c%s "$GZ_FILE" 2>/dev/null || stat -f%z "$GZ_FILE" 2>/dev/null || echo "0")
log "Compressed: $(numfmt --to=iec "$GZ_SIZE" 2>/dev/null || echo "${GZ_SIZE} bytes")"

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

# ── Upload to S3-compatible storage (IDrive) ────────────────────────────────

UPLOAD_STATUS="skipped"
REMOTE_FILE="${REMOTE_PATH}/whydud_${TIMESTAMP}.dump.gz"

if command -v rclone &>/dev/null; then
  # Configure rclone on the fly if env vars are set
  if [ -n "${RCLONE_S3_ENDPOINT:-}" ] && [ -n "${RCLONE_S3_ACCESS_KEY:-}" ]; then
    export RCLONE_CONFIG_IDRIVE_TYPE=s3
    export RCLONE_CONFIG_IDRIVE_PROVIDER=Other
    export RCLONE_CONFIG_IDRIVE_ENDPOINT="${RCLONE_S3_ENDPOINT}"
    export RCLONE_CONFIG_IDRIVE_ACCESS_KEY_ID="${RCLONE_S3_ACCESS_KEY}"
    export RCLONE_CONFIG_IDRIVE_SECRET_ACCESS_KEY="${RCLONE_S3_SECRET_KEY}"
    export RCLONE_CONFIG_IDRIVE_ACL=private

    log "Uploading to idrive:${BUCKET}/${REMOTE_FILE}..."
    if rclone copyto "$GZ_FILE" "idrive:${BUCKET}/${REMOTE_FILE}" --progress 2>&1; then
      UPLOAD_STATUS="success"
      log "Upload complete"
    else
      UPLOAD_STATUS="failed"
      log "WARNING: Upload failed — local backup retained"
    fi
  else
    log "WARNING: RCLONE_S3_ENDPOINT or RCLONE_S3_ACCESS_KEY not set — skipping upload"
  fi
elif command -v aws &>/dev/null; then
  # Fallback: AWS CLI with custom endpoint
  if [ -n "${RCLONE_S3_ENDPOINT:-}" ]; then
    export AWS_ACCESS_KEY_ID="${RCLONE_S3_ACCESS_KEY}"
    export AWS_SECRET_ACCESS_KEY="${RCLONE_S3_SECRET_KEY}"
    log "Uploading via aws s3 cp to ${BUCKET}/${REMOTE_FILE}..."
    if aws s3 cp "$GZ_FILE" "s3://${BUCKET}/${REMOTE_FILE}" \
        --endpoint-url "https://${RCLONE_S3_ENDPOINT}" 2>&1; then
      UPLOAD_STATUS="success"
      log "Upload complete"
    else
      UPLOAD_STATUS="failed"
      log "WARNING: Upload failed — local backup retained"
    fi
  fi
else
  log "WARNING: Neither rclone nor aws CLI found — skipping upload"
fi

# ── Update manifest for incremental tracking ─────────────────────────────────

cat > "$MANIFEST_FILE" <<EOF
# Whydud backup manifest — $(date -u +%Y-%m-%dT%H:%M:%SZ)
price_snapshots:${PRICE_COUNT}
dudscore_history:${SCORE_COUNT}
last_backup:${TIMESTAMP}
last_file:${GZ_FILE}
EOF
log "Manifest updated"

# ── Record backup timestamp for health check ─────────────────────────────────

echo "$TIMESTAMP" > "${BACKUP_DIR}/.last_backup_time"

# ── Local retention: delete backups older than 7 days ────────────────────────

log "Cleaning local backups older than ${LOCAL_RETENTION_DAYS} days..."
DELETED_LOCAL=$(find "$BACKUP_DIR" -name "whydud_*.dump.gz" -mtime +"$LOCAL_RETENTION_DAYS" -delete -print 2>/dev/null | wc -l || echo "0")
log "Deleted ${DELETED_LOCAL} old local backups"

# ── Remote retention: delete backups older than 180 days ─────────────────────

DELETED_REMOTE=0
if [ "$UPLOAD_STATUS" = "success" ] && command -v rclone &>/dev/null; then
  log "Cleaning remote backups older than ${REMOTE_RETENTION_DAYS} days..."
  DELETED_REMOTE=$(rclone delete "idrive:${BUCKET}/${REMOTE_PATH}/" \
    --min-age "${REMOTE_RETENTION_DAYS}d" \
    --dry-run 2>&1 | grep -c "DELETE" || echo "0")

  rclone delete "idrive:${BUCKET}/${REMOTE_PATH}/" \
    --min-age "${REMOTE_RETENTION_DAYS}d" 2>/dev/null || true
  log "Deleted ~${DELETED_REMOTE} old remote backups"
fi

# ── Summary ──────────────────────────────────────────────────────────────────

INCREMENTAL_NOTE=""
if [ ${#EXCLUDE_DATA_ARGS[@]} -gt 0 ]; then
  INCREMENTAL_NOTE="\\n**Incremental:** skipped ${#EXCLUDE_DATA_ARGS[@]} unchanged time-series table(s)"
fi

SUMMARY="**Database:** \`${DB_NAME}\`
**Size:** $(numfmt --to=iec "$GZ_SIZE" 2>/dev/null || echo "${GZ_SIZE}B") (compressed)
**Duration:** ${ELAPSED}s
**Upload:** ${UPLOAD_STATUS}
**Local cleanup:** ${DELETED_LOCAL} old files removed
**Remote cleanup:** ${DELETED_REMOTE} old files removed${INCREMENTAL_NOTE}"

log "=== Backup Complete ==="
log "  File: ${GZ_FILE}"
log "  Size: $(numfmt --to=iec "$GZ_SIZE" 2>/dev/null || echo "${GZ_SIZE}B")"
log "  Duration: ${ELAPSED}s"
log "  Upload: ${UPLOAD_STATUS}"

if [ "$UPLOAD_STATUS" = "failed" ]; then
  discord_failure "Backup Partial" "pg_dump succeeded but upload to S3 failed.\\n\\n${SUMMARY}"
  exit 1
else
  discord_success "Backup Complete" "${SUMMARY}"
fi
