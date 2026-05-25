import os
import time
import requests

API = 'https://api.render.com/v1'
SERVICE_NAME = os.getenv('RENDER_SERVICE_NAME') or 'mediflow-backend'
HEALTH_URL = os.getenv('HEALTH_URL') or 'https://mediflow-backend-r2c4.onrender.com/health'
METRICS_URL = os.getenv('METRICS_URL') or 'https://mediflow-backend-r2c4.onrender.com/api/v1/analytics/metrics'

def main():
    api_key = os.getenv('RENDER_API_KEY')
    if not api_key:
        print('RENDER_API_KEY not set')
        return 2

    headers = {'Authorization': f'Bearer {api_key}'}

    print('Listing services...')
    r = requests.get(f'{API}/services', headers=headers, timeout=30)
    if not r.ok:
        print('Failed to list services:', r.status_code, r.text)
        return 3

    services = r.json()
    svc = None
    for s in services:
        name = s.get('name') or ''
        if SERVICE_NAME in name or SERVICE_NAME == s.get('id'):
            svc = s
            break

    if not svc:
        print('Service not found by name:', SERVICE_NAME)
        # Print some candidates
        print('Available services (first 10):')
        for s in services[:10]:
            print('-', s.get('name'), s.get('id'))
        return 4

    service_id = svc['id']
    print('Found service:', svc.get('name'), service_id)

    print('Triggering deploy...')
    dr = requests.post(f'{API}/services/{service_id}/deploys', headers=headers, json={})
    if not dr.ok:
        print('Deploy trigger failed:', dr.status_code, dr.text)
        return 5

    deploy = dr.json()
    deploy_id = deploy.get('id')
    print('Deploy triggered, id:', deploy_id)

    # Poll health & metrics until metrics returns 200 or timeout
    for i in range(30):
        try:
            h = requests.get(HEALTH_URL, timeout=5)
            m = requests.get(METRICS_URL, headers={'Authorization': os.getenv('TEST_TOKEN','')}, timeout=10)
            print(f'[{i}] health={h.status_code} metrics={m.status_code}')
            if m.status_code == 200:
                print('Metrics endpoint is healthy.')
                return 0
        except Exception as e:
            print(f'[{i}] request error:', e)
        time.sleep(10)

    print('Timed out waiting for metrics to become healthy.')
    return 6


if __name__ == '__main__':
    raise SystemExit(main())
