# Environment Templates

Templates for local/dev/staging/prod configuration.

## Common usage
```bash
cp config/environments/development.env.template .env
```

## Notes
- Keep real secrets out of git.
- Service-specific templates live under `config/environments/services/`.
