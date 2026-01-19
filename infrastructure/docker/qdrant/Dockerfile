# Qdrant Vector Database with curl for healthchecks
# Base image: Official Qdrant v1.7.0
FROM qdrant/qdrant:v1.7.0

# Install curl for Docker healthcheck
RUN apt-get update && \
    apt-get install -y curl && \
    rm -rf /var/lib/apt/lists/*

# Use the default Qdrant entrypoint and command
# No CMD needed - inherited from base image
