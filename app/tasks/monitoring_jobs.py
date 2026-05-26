import asyncio
import logging
import psutil
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func, Integer
from app.core.database import SessionLocal
from app.services.notification_service import get_notification_service
from app.core.config import settings
from app.models.notifications import SystemMetric

logger = logging.getLogger(__name__)

async def monitor_ai_health(db: Session):
    """SA004: Monitor AI Service Health"""
    try:
        from app.services.ai_service import get_ai_service
        ai_service = get_ai_service(db)
        health = ai_service.get_ai_service_info()
        if not health["integration_status"]["groq_configured"]:
            get_notification_service(db).create_ai_service_down_notification(
                "Groq Llama 3.1", {"error": "API Key missing or invalid"}
            )
    except Exception as e:
        logger.error(f"AI Health Monitor Failed: {e}")

async def monitor_system_storage(db: Session):
    """SA006: System Storage Critical"""
    try:
        usage = psutil.disk_usage('/')
        if usage.percent >= 90:
            get_notification_service(db).create_storage_critical_notification(
                used_storage_gb=usage.used / (1024**3), 
                total_storage_gb=usage.total / (1024**3)
            )
    except Exception as e:
        logger.error(f"Storage Monitor Failed: {e}")

async def monitor_db_performance(db: Session):
    """SA005: Database Performance Alert"""
    try:
        ten_minutes_ago = datetime.now(timezone.utc) - timedelta(minutes=10)
        total_reqs = db.query(func.count(SystemMetric.id)).filter(
            SystemMetric.metric_name == "api_request",
            SystemMetric.created_at >= ten_minutes_ago
        ).scalar() or 0

        if total_reqs > 10:
            errors = db.query(func.count(SystemMetric.id)).filter(
                SystemMetric.metric_name == "api_request",
                SystemMetric.created_at >= ten_minutes_ago,
                SystemMetric.details["status"].astext.cast(Integer) >= 500
            ).scalar() or 0

            error_rate = errors / total_reqs
            if error_rate > 0.10:
                get_notification_service(db).create_database_performance_alert_notification(
                    error_rate=error_rate,
                    details={"query_count": int(total_reqs), "slow_queries": int(errors)}
                )
    except Exception as e:
        logger.error(f"DB Performance Monitor Failed: {e}")

async def run_monitoring_loop():
    """Main background loop for SA004-SA009"""
    while True:
        db = SessionLocal()
        try:
            await monitor_ai_health(db)
            await monitor_system_storage(db)
            await monitor_db_performance(db)
        except Exception as e:
            logger.error(f"Monitoring Loop Error: {e}")
        finally:
            db.close()
        await asyncio.sleep(300) 

def start_monitoring():
    asyncio.create_task(run_monitoring_loop())