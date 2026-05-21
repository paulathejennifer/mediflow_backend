---
name: testing-deployment
description: Test the MediFlow Backend Docker deployment setup end-to-end. Use when verifying Dockerfile, docker-compose, Render config, or memory/startup changes.
---

# Testing MediFlow Backend Deployment

## Prerequisites

- Docker and Docker Compose must be available
- No external credentials needed for local deployment testing
- For Render deploy testing, the user must have a Render account and connect the repo

## Key Architecture Notes

- **FastAPI + SQLAlchemy + PostgreSQL** backend with AI services (Groq, Whisper, Tesseract OCR)
- **Whisper/PyTorch are lazy-loaded** — they are NOT imported at module level. The `SpeechAIService.__init__` does NOT load the model; it only loads on first `transcribe_audio()` call via `_ensure_model()`. This is critical for staying under Render free tier's 512MB RAM limit.
- **Gunicorn with Uvicorn workers** in production; plain Uvicorn in development
- `WEB_CONCURRENCY` env var controls worker count (default capped at `min(cpu_count + 1, 3)`)
- `start.sh` handles: wait for DB → create tables → run Alembic migrations → start server

## Test Procedures

All tests are shell-based (no GUI recording needed).

### 1. Docker Build
```bash
docker build -t mediflow-test .
```
Expect: exit code 0. Key things that might break:
- `openai-whisper` needs `--no-build-isolation` flag (its setup.py uses `pkg_resources`)
- PyTorch must be installed before whisper (`--index-url https://download.pytorch.org/whl/cpu` for CPU-only)
- Runtime image needs `libgl1` (not `libgl1-mesa-glx` which doesn't exist in slim images)

### 2. Verify Lazy Loading (OOM Fix)
```bash
docker run --rm -e DATABASE_URL=sqlite:///test.db mediflow-test python -c "
from app.services.speech_ai_service import speech_ai_service
import sys
print(f'whisper_loaded={\"whisper\" in sys.modules}')
print(f'torch_loaded={\"torch\" in sys.modules}')
"
```
Expect: both `False`. If either is `True`, the lazy loading is broken and the app will OOM on Render free tier.

### 3. Docker Compose (PostgreSQL + API)
```bash
docker compose up -d --build
sleep 15
curl -s http://localhost:8000/health
docker stats --no-stream --format "{{.Name}}: {{.MemUsage}}"
docker compose down -v
```
Expect:
- Health returns `{"status":"healthy","service":"mediflow-backend"}`
- App memory under ~200MB (well below 512MB Render limit)
- Note: Alembic migrations might fail if the migration chain is broken — this is a pre-existing issue, not a deployment config problem. The app still starts.

### 4. Config Hardening
```bash
# Production mode must require SECRET_KEY
docker run --rm -e DATABASE_URL=sqlite:///test.db mediflow-test python -c "
from app.core.config import Settings
try:
    Settings(ENVIRONMENT='production', SECRET_KEY='')
    print('FAIL')
except ValueError:
    print('PASS')
"

# Dev mode auto-generates SECRET_KEY
docker run --rm -e DATABASE_URL=sqlite:///test.db mediflow-test python -c "
from app.core.config import Settings
s = Settings(ENVIRONMENT='development', SECRET_KEY='')
print(f'key_generated={len(s.SECRET_KEY) > 0}')
"
```

### 5. render.yaml Validation
```bash
python3 -c "
import yaml
with open('render.yaml') as f:
    c = yaml.safe_load(f)
svc = c['services'][0]
assert svc['plan'] == 'free'
db_var = [v for v in svc['envVars'] if v['key'] == 'DATABASE_URL'][0]
assert db_var['fromDatabase']['property'] == 'connectionString'  # NOT connectionURI
assert 'disk' not in svc  # free tier doesn't support disks
wc = [v for v in svc['envVars'] if v['key'] == 'WEB_CONCURRENCY'][0]
assert wc['value'] == '1'
print('PASS')
"
```

## Common Issues

- **`openai-whisper` build fails with `ModuleNotFoundError: No module named 'pkg_resources'`**: Use `--no-build-isolation` flag when pip installing whisper
- **OOM on Render free tier**: Ensure Whisper/PyTorch are lazy-loaded (not imported at module top level in `speech_ai_service.py`)
- **`connectionURI` error on Render**: Render uses `connectionString`, not `connectionURI`
- **`disk` not supported on free tier**: Remove any `disk` config from render.yaml for free plan
- **`libgl1-mesa-glx` not found**: Use `libgl1` instead in Dockerfile (slim images)

## Devin Secrets Needed

None for local Docker testing. For live Render deployment:
- `GROQ_API_KEY` — set in Render dashboard for AI features
- `SMTP_USERNAME` / `SMTP_PASSWORD` — optional, for email notifications
