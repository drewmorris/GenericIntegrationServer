FROM python:3.11-bullseye

# Avoid interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install common dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        git \
        curl \
        sudo \
        less \
        nano \
        gnupg \
        dirmngr \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20 (includes npm) via NodeSource
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g npm@latest \
    && rm -rf /var/lib/apt/lists/*

# Install build-essential, SSL and Postgres headers, and Docker CLI for Testcontainers
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libssl-dev \
        libffi-dev \
        libpq-dev \
        docker.io \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements ./requirements
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements/default.txt -r requirements/dev.txt

# Install Poetry (global) for developer workflows
RUN pip install --no-cache-dir poetry && poetry --version
ENV POETRY_VIRTUALENVS_CREATE=false
ENV POETRY_NO_INTERACTION=1

# Create a vscode user with sudo privileges
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME -s /bin/bash \
    && usermod -aG docker $USERNAME \
    && echo "$USERNAME ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME

# Set work directory
WORKDIR /workspaces/GenericIntegrationServer

# Switch to the non-root user
USER $USERNAME

# Default command
CMD ["bash"] 