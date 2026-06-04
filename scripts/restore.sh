#!/usr/bin/env bash

# ====================================================================
# PostgreSQL Docker Database Restore Script
# ====================================================================
# This script restores a database from a gzipped sql backup file.
# Warning: This will overwrite data in the active database.
# Usage: sudo bash restore.sh /path/to/backup.sql.gz

set -euo pipefail

ENV_FILE="/srv/api/.env" # Path to environment variables file on server
CONTAINER_NAME="db_service"

echo "=== Starting DB Restore Process ==="

# 1. Verify Argument
if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <path_to_backup_file.sql.gz>" >&2
  exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "${BACKUP_FILE}" ]; then
  echo "[ERROR] Backup file '${BACKUP_FILE}' does not exist." >&2
  exit 1
fi

# 2. Load environment variables
if [ -f "${ENV_FILE}" ]; then
  export $(grep -v '^#' "${ENV_FILE}" | xargs)
else
  echo "[ERROR] Environment file ${ENV_FILE} not found. Cannot proceed." >&2
  exit 1
fi

DB_USER="${POSTGRES_USER:-postgres}"
DB_NAME="${POSTGRES_DB:-ai_gateway}"

# Verify container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
  echo "[ERROR] Database container '${CONTAINER_NAME}' is not running." >&2
  exit 1
fi

# 3. Confirmation warning (Critical for preventing accidental loss)
echo "--------------------------------------------------------"
echo "WARNING: You are about to restore the database from: ${BACKUP_FILE}"
echo "This will overwrite existing database records in '${DB_NAME}'!"
echo "--------------------------------------------------------"
read -p "Are you sure you want to proceed? (y/N): " -r CONFIRM

if [[ ! "${CONFIRM}" =~ ^[Yy]$ ]]; then
  echo "[INFO] Restore operation cancelled by user."
  exit 0
fi

# 4. Perform Restore
echo "[INFO] Restoring database '${DB_NAME}'..."

# Unzip and pipe into psql
if gunzip -c "${BACKUP_FILE}" | docker exec -i "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" > /dev/null; then
  echo "[SUCCESS] Database restore complete."
else
  echo "[ERROR] Database restore failed." >&2
  exit 1
fi
