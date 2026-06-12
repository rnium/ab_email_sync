#!/bin/sh
set -e

if [ -n "$DB_DIR" ]; then
    mkdir -p "$DB_DIR"
fi

echo "Running migrations..."
python manage.py migrate --noinput

echo "Seeding configuration..."
python manage.py seed_configurations

echo "Starting: $*"
exec "$@"
