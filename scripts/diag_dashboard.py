import os
import sys
import traceback
from datetime import datetime, timedelta

# Ensure project root is on path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ['DATABASE_URL'] = os.getenv('DATABASE_URL') or 'postgresql://mediflow:9d2vcMX1T6MkocVV27WFljmhPPU7bJzY@dpg-d87lop1s16ns73aau640-a.oregon-postgres.render.com/mediflow_pzoh'

from app.core.database import engine, SessionLocal
from app.models.referral import Referral
from app.models.patient import Patient
from app.models.facility import Facility


def run():
    try:
        db = SessionLocal()
        days = 30
        start_date = datetime.utcnow() - timedelta(days=days)
        referral_query = db.query(Referral)
        patient_query = db.query(Patient)
        facility_query = db.query(Facility)

        print('count patients...')
        total_patients = patient_query.count()
        print('patients:', total_patients)

        print('count facilities...')
        total_facilities = facility_query.count()
        print('facilities:', total_facilities)

        print('count referrals in 30d...')
        total_referrals = referral_query.filter(Referral.created_at >= start_date).count()
        print('referrals 30d:', total_referrals)

        print('active referrals count...')
        active_statuses = [
            'draft', 'submitted', 'accepted', 'in_transit', 'received'
        ]
        active_referrals = referral_query.filter(Referral.status.in_(active_statuses)).count()
        print('active_referrals:', active_referrals)

        print('pending referrals...')
        pending_referrals = referral_query.filter(Referral.status == 'submitted').count()
        print('pending_referrals:', pending_referrals)

        print('computing rejection rate...')
        total_with_outcome = referral_query.filter(Referral.status.in_(['completed','rejected'])).count()
        rejected_count = referral_query.filter(Referral.status == 'rejected').count()
        print('total_with_outcome,rejected', total_with_outcome, rejected_count)

        print('avg_referrals_per_facility...')
        avg_referrals_per_facility = total_referrals / max(total_facilities, 1)
        print(avg_referrals_per_facility)

    except Exception:
        traceback.print_exc()
    finally:
        try:
            db.close()
        except Exception:
            pass

if __name__ == '__main__':
    run()
