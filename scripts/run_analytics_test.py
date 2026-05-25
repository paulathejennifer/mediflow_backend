import os
import sys
import traceback

# Ensure project root is on path
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "\..")

from app.core.database import SessionLocal
from fastapi.security import HTTPAuthorizationCredentials
from app.core.dependencies import get_current_user
from app.api.v1.endpoints import analytics as analytics_module

os.environ['DATABASE_URL'] = os.getenv('DATABASE_URL') or 'postgresql://mediflow:9d2vcMX1T6MkocVV27WFljmhPPU7bJzY@dpg-d87lop1s16ns73aau640-a.oregon-postgres.render.com/mediflow_pzoh'


def run():
    db = SessionLocal()
    try:
        # Simulate dependency resolution using a bearer token
        token = os.getenv('TEST_TOKEN') or 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZXhwIjoxNzc5NjgzNzU0LCJ0eXBlIjoiYWNjZXNzIn0.0KXprCJxyKdNY_80dCpT3j3izi1DRGxSMjZqfs0n9u8'
        creds = HTTPAuthorizationCredentials(scheme='Bearer', credentials=token)
        try:
            user = get_current_user(credentials=creds, db=db)
        except Exception as e:
            print('get_current_user raised:', type(e), getattr(e, 'detail', repr(e)))
            raise
        print('Resolved user:', user.email, user.role)
        print('Calling get_dashboard_kpis...')
        res = analytics_module.get_dashboard_kpis(db=db, current_user=user)
        print('Result:', res)
    except Exception:
        traceback.print_exc()
    finally:
        db.close()


if __name__ == '__main__':
    run()
