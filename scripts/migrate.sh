#!/bin/bash
# Run from the backend/ directory: bash ../scripts/migrate.sh

set -e

echo "Running Alembic migrations..."
cd "$(dirname "$0")/../backend"
alembic upgrade head
echo "Migrations complete."