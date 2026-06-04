#!/usr/bin/env bash

# ====================================================================
# PostgreSQL Automated Docker Backup Script
# ====================================================================
# This script executes a pg_dump of the database running in Docker,
# gzips the output, saves it in a local directory, and removes backups
# older than 7 days.
# Recommended: Set up as a daily Cron job on your VPS.

set -euo pipefail

# 1. Configuration
BACKUP_DIR="/srv/backups/db"
KEEP_DAYS=7
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/db_backup_${TIMESTAMP}.sql.gz"
ENV_FILE="/srv/api/.env" # Path to environment variables file on server

echo "=== Starting DB Backup: $(date) ==="

# Ensure backup directory exists
mkdir -p "${BACKUP_DIR}"

# 2. Load environment variables for DB credentials
if [ -f "${ENV_FILE}" ]; then
  # Load env variables, ignoring comments
  export $(grep -v '^#' "${ENV_FILE}" | xargs)
else
  echo "[ERROR] Environment file ${ENV_FILE} not found. Cannot proceed with backup." >&2
  exit 1
fi

DB_USER="${POSTGRES_USER:-postgres}"
DB_NAME="${POSTGRES_DB:-ai_gateway}"
CONTAINER_NAME="db_service"

# Check if PostgreSQL container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
  echo "[ERROR] Database container '${CONTAINER_NAME}' is not running." >&2
  exit 1
fi

# 3. Perform dump inside container and compress on host
echo "[INFO] Dumping database '${DB_NAME}' from container '${CONTAINER_NAME}'..."
if docker exec -t "${CONTAINER_NAME}" pg_dump -U "${DB_USER}" -d "${DB_NAME}" | gzip > "${BACKUP_FILE}"; then
  echo "[SUCCESS] Backup saved to: ${BACKUP_FILE}"
  echo "[INFO] Backup size: $(du -sh "${BACKUP_FILE}" | cut -f1)"
else
  echo "[ERROR] Backup process failed." >&2
  exit 1
fi

# 4. Prune old backups
echo "[INFO] Cleaning up backups older than ${KEEP_DAYS} days..."
find "${BACKUP_DIR}" -name "db_backup_*.sql.gz" -mtime +${KEEP_DAYS} -delete
echo "[INFO] Clean up complete."

echo "=== Backup Process Completed: $(date) ==="
