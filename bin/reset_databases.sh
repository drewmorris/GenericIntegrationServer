#!/bin/bash
set -e

echo "Stopping and removing existing containers..."
docker-compose down -v

echo "Starting fresh database services..."
docker-compose up -d

echo "Waiting for services to be ready..."
timeout=60
elapsed=0

while [ $elapsed -lt $timeout ]; do
    if docker-compose exec -T postgres pg_isready -U postgres >/dev/null 2>&1 && \
       docker-compose exec -T redis redis-cli ping >/dev/null 2>&1; then
        echo "Services are ready!"
        break
    fi
    sleep 2
    elapsed=$((elapsed + 2))
done

if [ $elapsed -ge $timeout ]; then
    echo "Timeout waiting for services to be ready"
    exit 1
fi

echo "Database services reset successfully!"
echo "PostgreSQL: localhost:5432 (user: postgres, password: postgres, db: integration_server)"
echo "Redis: localhost:6379"

