#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env}"
BACKUP_DIR="${BACKUP_DIR:-$ROOT_DIR/backups/postgres}"
TIMESTAMP="$(date +"%Y%m%d_%H%M%S")"
BACKUP_FILE="$BACKUP_DIR/competitor_analysis_${TIMESTAMP}.sql.gz"
CONTAINER_NAME="${POSTGRES_CONTAINER_NAME:-competitor_postgres}"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

mkdir -p "$BACKUP_DIR"

: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_DB:?POSTGRES_DB is required}"

echo "Creating backup at $BACKUP_FILE"
docker exec "$CONTAINER_NAME" pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists | gzip > "$BACKUP_FILE"

if [[ -n "${BACKUP_S3_URI:-}" ]]; then
  if command -v aws >/dev/null 2>&1; then
    echo "Uploading backup to $BACKUP_S3_URI"
    aws s3 cp "$BACKUP_FILE" "$BACKUP_S3_URI/$(basename "$BACKUP_FILE")"
  else
    echo "aws cli not found; skipping S3 upload" >&2
  fi
fi

echo "Backup completed: $BACKUP_FILE"
