# Secrets and environment configuration

This project must not store real broker credentials directly in Python source files.

## Recommended pattern

1. Copy `.env.example` to `.env`
2. Put real credentials in `.env`
3. Keep `.env` outside Git tracking
4. Load values via `os.getenv(...)` in `config.py`

## Required variables

- `TOSS_CLIENT_ID`
- `TOSS_CLIENT_SECRET`
- `TOSS_ACCOUNT_NUMBER`
- `TOSS_ACCOUNT_PASSWORD`
- `TOSS_ACCOUNT_SEQ`
- `TOSS_BASE_URL`
- `TOSS_TOKEN_URL`

## Recommended production pattern

Use a secret manager such as:
- AWS Secrets Manager
- Azure Key Vault
- GCP Secret Manager
- Kubernetes Secrets
- CI/CD secret variables

## Security rules

- Never commit real credentials to Git
- Never print secrets to logs
- Never include secrets in screenshots or issue reports
- Keep `.env` in `.gitignore`
- Use environment variables in deployment, not source files

## Local setup on Windows PowerShell

```powershell
Copy-Item .env.example .env
notepad .env
```

Or run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\set_env_example.ps1
```
