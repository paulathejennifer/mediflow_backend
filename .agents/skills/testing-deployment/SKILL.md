---
name: testing-deployment
description: Test MediFlow Backend deployment setup end-to-end. Use when verifying Docker, docker-compose, Render config, or deployment-related changes.
---

# Testing MediFlow Backend Deployment

## Overview
MediFlow Backend is a FastAPI + SQLAlchemy + PostgreSQL app with Google Speech Recognition, Groq AI, Tesseract OCR, and WebSocket notifications. Deployment uses Docker + Render.com free tier (512MB RAM limit).

## Prerequisites
- Docker and docker-compose installed
- No external credentials needed for deployment testing (all local)

## Quick Test Sequence

### 1. Docker Build
```bash
cd /path/to/mediflow_backend
docker build --no-cache -t mediflow-test .
# Expect: exit code 0, ~45s build time
```

### 2. Docker Compose (PostgreSQL + API)
```bash
docker compose up -d --build
sleep 12  # Wait for DB init + app startup
curl -s http://localhost:8000/health
# Expect: {"status":"healthy","service":"mediflow-backend"}
```

### 3. Verify No Import Errors
```bash
docker compose logs app | grep -c "ModuleNotFoundError"
# Expect: 0
docker compose logs app | grep "Application startup complete"
# Expect: match found
```

### 4. Swagger Docs (proves all routers registered)
```bash
curl -s http://localhost:8000/docs | grep -c "swagger-ui"
# Expect: > 0
```

### 5. API Endpoint Check
```bash
curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" -d '{}'
# Expect: HTTP 422 with validation errors (not 404 or 500)
```

### 6. Memory Check (Render free tier = 512MB)
```bash
docker stats --no-stream --format "{{.Name}}: {{.MemUsage}}"
# Expect: app container < 200 MiB
```

### 7. Config Hardening
```bash
docker run --rm --entrypoint python mediflow-test -c "
import os
os.environ['ENVIRONMENT'] = 'production'
os.environ['DATABASE_URL'] = 'postgresql://x:x@localhost/x'
try:
    from app.core.config import Settings
    s = Settings()
    print('FAIL: No ValueError raised')
except ValueError as e:
    print(f'PASS: {e}')
"
# Expect: ValueError about SECRET_KEY
```

### 8. render.yaml Validation
```bash
python3 -c "
import yaml
with open('render.yaml') as f:
    cfg = yaml.safe_load(f)
svc = cfg['services'][0]
env_vars = {e['key']: e for e in svc['envVars']}
assert env_vars['DATABASE_URL']['fromDatabase']['property'] == 'connectionString'
assert 'disk' not in svc
assert env_vars['WEB_CONCURRENCY']['value'] == '1'
assert svc['plan'] == 'free'
print('ALL CHECKS PASSED')
"
```

### 9. Cleanup
```bash
docker compose down -v
```

## Common Issues
- **Migration warnings** about duplicate columns are non-fatal. The `start.sh` script treats migration failures as non-fatal.
- **PyAudio** requires `portaudio19-dev` (build) and `libportaudio2` (runtime) in Docker.
- **`.gitignore`** had `models/` which accidentally excluded `app/models/`. Fixed to `/models/` (root only).
- The app previously used OpenAI Whisper + PyTorch which caused OOM on Render free tier. Now uses Google Speech Recognition (much lighter).

## Render Deployment
- Free tier: 512MB RAM, no persistent disks
- Use `connectionString` (not `connectionURI`) in render.yaml
- Set `WEB_CONCURRENCY=1` to avoid duplicating app memory across workers
- Set `GROQ_API_KEY`, `SMTP_USER`, `SMTP_PASSWORD` in Render dashboard

## Devin Secrets Needed
None for local deployment testing. For live Render testing, the user needs to configure `GROQ_API_KEY`, `SMTP_USER`, and `SMTP_PASSWORD` in the Render dashboard.
