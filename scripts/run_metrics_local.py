import os
import traceback
import sys
import requests
# Ensure project root is on path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.database import SessionLocal
from app.core.security import verify_token
from app.api.v1.endpoints import analytics as analytics_module
from app.models.user import User

BASE = os.getenv('BASE_URL','https://mediflow-backend-r2c4.onrender.com')
LOGIN = BASE + '/api/v1/auth/login'

cred = {'email':'admin@mediflow.com','password':'admin123'}

try:
    print('Logging in...')
    r = requests.post(LOGIN, json=cred, timeout=10)
    print('LOGIN', r.status_code)
    if not r.ok:
        print('Login failed, body:', r.text)
        raise SystemExit(1)
    token = r.json().get('access_token')
    print('Token length', len(token))

    # Use /auth/me to get the user info from the server (avoids decoding JWT locally)
    me = requests.get(BASE + '/api/v1/auth/me', headers={'Authorization': f'Bearer {token}'}, timeout=10)
    print('/auth/me', me.status_code, me.text)
    if not me.ok:
        print('Failed to get /auth/me')
        raise SystemExit(1)
    user_id = int(me.json().get('id'))

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        print('Fetched user:', user.email, user.role)
        print('Calling get_analytics_metrics directly...')
        try:
            res = analytics_module.get_analytics_metrics(db=db, current_user=user)
            print('Result:', res)
        except Exception:
            traceback.print_exc()
    finally:
        db.close()
except Exception:
    traceback.print_exc()
