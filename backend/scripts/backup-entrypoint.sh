#!/usr/bin/env bash
#
# backup-entrypoint.sh — Docker entrypoint for the backup sidecar container.
#
# Installs rclone once, then runs backup.sh every 6 hours in a loop.
# This is more reliable than cron in Docker (no daemon, env vars inherited).

set -euo pipefail

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] ENTRYPOINT: $*"; }

# ── Install rclone if missing ────────────────────────────────────────────────
if ! command -v rclone &>/dev/null; then
  log "Installing rclone..."
  apt-get update -qq && apt-get install -y -qq rclone > /dev/null 2>&1
  log "rclone installed: $(rclone version | head -1)"
else
  log "rclone already available: $(rclone version | head -1)"
fi

# ── Validate required env vars ───────────────────────────────────────────────
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"

if [ -z "${RCLONE_S3_ENDPOINT:-}" ]; then
  log "WARNING: RCLONE_S3_ENDPOINT not set — backups will be local only"
fi

# ── Ensure backup script is executable ───────────────────────────────────────
chmod +x /scripts/backup.sh

INTERVAL="${BACKUP_INTERVAL_SECONDS:-21600}"  # default 6 hours
log "Backup service started. Interval: ${INTERVAL}s ($(( INTERVAL / 3600 ))h)"
log "Database: ${POSTGRES_DB:-whydud}@${POSTGRES_HOST:-postgres}:${POSTGRES_PORT:-5432}"

# ── Run first backup after a short delay (let postgres fully warm up) ────────
sleep 30

# ── Loop forever ─────────────────────────────────────────────────────────────
while true; do
  log "Starting backup cycle..."
  /scripts/backup.sh 2>&1 || log "Backup failed — will retry next cycle"
  log "Next backup in ${INTERVAL}s"
  sleep "$INTERVAL"
done
