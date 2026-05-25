import os, time, requests

HEALTH_URL = 'https://mediflow-backend-r2c4.onrender.com/health'
METRICS_URL = 'https://mediflow-backend-r2c4.onrender.com/api/v1/analytics/metrics'
TOKEN = os.getenv('TEST_TOKEN') or 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZXhwIjoxNzc5NjgzNzU0LCJ0eXBlIjoiYWNjZXNzIn0.0KXprCJxyKdNY_80dCpT3j3izi1DRGxSMjZqfs0n9u8'

for i in range(12):
    try:
        r = requests.get(HEALTH_URL, timeout=5)
        print(f"[{i}] HEALTH {r.status_code} {r.text}")
    except Exception as e:
        print(f"[{i}] HEALTH ERROR: {e}")
    try:
        r = requests.get(METRICS_URL, headers={'Authorization': f'Bearer {TOKEN}'}, timeout=10)
        body = r.text
        print(f"[{i}] METRICS {r.status_code} \n{body}\n---")
    except Exception as e:
        print(f"[{i}] METRICS ERROR: {e}")
    if r.status_code == 200:
        break
    time.sleep(10)
