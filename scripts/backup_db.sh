#!/bin/bash
# Nightly PostgreSQL backup for recordered
# Run via cron: 0 3 * * * /var/www/recorder_ed/scripts/backup_db.sh
#
# Dumps the database to backups/, prunes dumps older than RETENTION_DAYS.
# The whole-server Backup Package picks this folder up on its own schedule
# and ships it offsite — this script only needs to produce a local file.

PROJECT_DIR="/var/www/recorder_ed"
BACKUP_DIR="${PROJECT_DIR}/backups"
LOG_DIR="${PROJECT_DIR}/logs"
LOG_FILE="${LOG_DIR}/db_backup.log"
RETENTION_DAYS=14

mkdir -p "$BACKUP_DIR" "$LOG_DIR"
chmod 700 "$BACKUP_DIR"

echo "" >> "$LOG_FILE"
echo "===== $(date '+%Y-%m-%d %H:%M:%S') =====" >> "$LOG_FILE"

cd "$PROJECT_DIR" || {
    echo "Failed to cd to $PROJECT_DIR" >> "$LOG_FILE"
    exit 1
}

set -a
source .env
set +a

if [ -z "$DB_NAME" ] || [ -z "$DB_USER" ] || [ -z "$DB_PASSWORD" ]; then
    echo "Missing DB_NAME/DB_USER/DB_PASSWORD after sourcing .env" >> "$LOG_FILE"
    exit 1
fi

TIMESTAMP=$(date '+%Y-%m-%d_%H%M%S')
DUMP_FILE="${BACKUP_DIR}/recordered_${TIMESTAMP}.sql.gz"

PGPASSWORD="$DB_PASSWORD" pg_dump \
    -h "${DB_HOST:-localhost}" \
    -p "${DB_PORT:-5432}" \
    -U "$DB_USER" \
    "$DB_NAME" | gzip > "$DUMP_FILE"

DUMP_STATUS=${PIPESTATUS[0]}

if [ "$DUMP_STATUS" -ne 0 ]; then
    echo "pg_dump failed with exit code $DUMP_STATUS" >> "$LOG_FILE"
    rm -f "$DUMP_FILE"
    exit 1
fi

chmod 600 "$DUMP_FILE"
echo "Backup succeeded: $DUMP_FILE ($(du -h "$DUMP_FILE" | cut -f1))" >> "$LOG_FILE"

DELETED=$(find "$BACKUP_DIR" -name "recordered_*.sql.gz" -mtime "+${RETENTION_DAYS}" -print -delete)
if [ -n "$DELETED" ]; then
    echo "Pruned old backups:" >> "$LOG_FILE"
    echo "$DELETED" >> "$LOG_FILE"
fi

echo "Backup completed" >> "$LOG_FILE"
