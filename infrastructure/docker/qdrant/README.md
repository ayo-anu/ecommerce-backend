# Qdrant Image

Custom image that adds `curl` for health checks. Base is `qdrant/qdrant:v1.7.0`.

## Build
```bash
docker compose -f deploy/docker/compose/base.yml build qdrant
```
