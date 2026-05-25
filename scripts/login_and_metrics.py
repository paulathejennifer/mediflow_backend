import os
import requests

BASE = os.getenv('BASE_URL','https://mediflow-backend-r2c4.onrender.com')
LOGIN = BASE + '/api/v1/auth/login'
METRICS = BASE + '/api/v1/analytics/metrics'

cred = {'email':'admin@mediflow.com','password':'admin123'}

print('Logging in...')
r = requests.post(LOGIN, json=cred, timeout=10)
print('LOGIN', r.status_code, r.text)
if r.ok:
    token = r.json().get('access_token')
    print('Got token length', len(token or ''))
    h = {'Authorization': f'Bearer {token}'}
    rm = requests.get(METRICS, headers=h, timeout=10)
    print('METRICS', rm.status_code)
    print(rm.text)
else:
    print('Login failed')
