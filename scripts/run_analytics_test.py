import os
import sys
import traceback

# Ensure project root is on path
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "\..")

from app.core.database import SessionLocal
from app.models.user import User
from app.api.v1.endpoints import analytics as analytics_module

os.environ['DATABASE_URL'] = os.getenv('DATABASE_URL') or 'postgresql://mediflow:9d2vcMX1T6MkocVV27WFljmhPPU7bJzY@dpg-d87lop1s16ns73aau640-a.oregon-postgres.render.com/mediflow_pzoh'


def run():
    db = SessionLocal()
    try:
        # Build a super admin user
        user = User(id=1, first_name='Super', last_name='Admin', email='admin@mediflow.com', role='super_admin')
        print('Calling get_dashboard_kpis...')
        res = analytics_module.get_dashboard_kpis(db=db, current_user=user)
        print('Result:', res)
    except Exception:
        traceback.print_exc()
    finally:
        db.close()


if __name__ == '__main__':
    run()
