import requests

BASE = 'https://mediflow-backend-r2c4.onrender.com'
CRED = {'email': 'admin@mediflow.com', 'password': 'admin123'}
ENDPOINTS = [
    '/api/v1/auth/me',
    '/api/v1/analytics/metrics',
    '/api/v1/analytics/dashboard',
    '/api/v1/analytics/referrals/by-status',
    '/api/v1/analytics/referrals/by-priority',
    '/api/v1/analytics/system-activity',
]

try:
    print('Logging in...')
    r = requests.post(BASE + '/api/v1/auth/login', json=CRED, timeout=20)
    print('LOGIN', r.status_code, r.text[:400])
    if not r.ok:
        raise SystemExit('Login failed')
    token = r.json().get('access_token')
    if not token:
        raise SystemExit('No access token returned')

    headers = {'Authorization': f'Bearer {token}'}
    for path in ENDPOINTS:
        try:
            rr = requests.get(BASE + path, headers=headers, timeout=20)
            print(path, rr.status_code)
            print(rr.text[:800])
        except Exception as exc:
            print(path, 'ERROR', exc)
except Exception as exc:
    print('ERROR', exc)
