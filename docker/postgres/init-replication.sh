#!/bin/bash
set -e

# Create the replication user if it doesn't exist.
# REPLICATOR_PASSWORD must be set in the environment (.env file).
if [ -z "$REPLICATOR_PASSWORD" ]; then
  echo "WARNING: REPLICATOR_PASSWORD not set, skipping replication user creation"
  exit 0
fi

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    DO \$\$
    BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'replicator') THEN
      CREATE USER replicator WITH REPLICATION ENCRYPTED PASSWORD '${REPLICATOR_PASSWORD}';
      RAISE NOTICE 'Created replication user: replicator';
    END IF;
    END
    \$\$;
EOSQL
