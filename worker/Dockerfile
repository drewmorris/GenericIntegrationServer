FROM python:3.11-slim

# Install runtime deps only (no dev)
WORKDIR /app
COPY pyproject.toml poetry.lock /app/
RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry install --without dev --only main

# Copy source
COPY . /app

# Default command: Celery worker with two processes
CMD ["celery", "-A", "backend.orchestrator", "worker", "-Q", "default", "-l", "info", "--concurrency=2"] 