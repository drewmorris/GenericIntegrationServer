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
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20 (includes npm) via NodeSource
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g npm@latest \
    && rm -rf /var/lib/apt/lists/*

# Create a vscode user with sudo privileges
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME -s /bin/bash \
    && echo "$USERNAME ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME

# Set work directory
WORKDIR /workspaces/GenericIntegrationServer

# Switch to the non-root user
USER $USERNAME

# Default command
CMD ["bash"] 