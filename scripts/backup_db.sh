#!/usr/bin/env bash
# ==============================================================================
# ATHINA NIGHTLY DATABASE BACKUP SCRIPT
# Dumps PostgreSQL database, compresses, and pushes to Ratul's Telegram Storage
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$ROOT_DIR/backend/.env"

if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs -d '\n' || true)
fi

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="$ROOT_DIR/backups"
BACKUP_FILE="$BACKUP_DIR/athina_db_$TIMESTAMP.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "[*] Starting Athina database dump: $TIMESTAMP"

# Execute pg_dump via docker or local postgres
if docker ps --format '{{.Names}}' | grep -q "athina_db"; then
    docker exec -t athina_db pg_dump -U "${POSTGRES_USER:-athina}" "${POSTGRES_DB:-athina}" | gzip > "$BACKUP_FILE"
else
    echo "[!] Warning: athina_db container not running, attempting local pg_dump"
    pg_dump -U "${POSTGRES_USER:-athina}" "${POSTGRES_DB:-athina}" | gzip > "$BACKUP_FILE"
fi

FILE_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "[+] Backup successfully created: $BACKUP_FILE ($FILE_SIZE)"

# Retain last 7 days of local backups
find "$BACKUP_DIR" -type f -name "athina_db_*.sql.gz" -mtime +7 -delete

# Push backup to Telegram Channel if configured
if [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_BACKUP_CHANNEL_ID:-}" ]; then
    echo "[*] Pushing backup to private Telegram storage channel ($TELEGRAM_BACKUP_CHANNEL_ID)..."
    curl -s -F "chat_id=$TELEGRAM_BACKUP_CHANNEL_ID" \
            -F "caption=Athina Database Nightly Backup: $TIMESTAMP ($FILE_SIZE)" \
            -F "document=@$BACKUP_FILE" \
            "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendDocument" > /dev/null
    echo "[+] Backup sent to Telegram successfully!"
fi

echo "[✓] All backup tasks finished."
