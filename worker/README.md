# Integration-Server Celery Worker

This image runs the background task processor responsible for executing connector sync jobs.

Usage (local):
```bash
# Build
docker build -f worker/Dockerfile -t integration-worker:dev .

# Run with required services
export REDIS_URL=redis://localhost:6379/0
export POSTGRES_HOST=localhost
export POSTGRES_DB=integration_server
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=postgres

docker run --network=host --env REDIS_URL --env POSTGRES_HOST --env POSTGRES_DB \
           --env POSTGRES_USER --env POSTGRES_PASSWORD integration-worker:dev
```

In CI the image is built and the test-suite is executed against it (see `.github/workflows/worker.yml`). 