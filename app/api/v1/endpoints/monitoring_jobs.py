import asyncio
import logging
import psutil
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, Integer
from app.core.database import SessionLocal
from app.services.notification_service import get_notification_service
from app.core.config import settings
from app.models.notifications import SystemMetric

logger = logging.getLogger(__name__)

async def monitor_ai_health(db: Session):
    """SA004: Monitor AI Service Health"""
    notif_service = get_notification_service(db)
    # This is a heuristic check - in prod, call the actual AI health endpoints
    try:
        # Placeholder for health check logic
        ai_healthy = True 
        if not ai_healthy:
            notif_service.create_ai_service_down_notification("Groq Llama 3.1", "API Error")
    except Exception as e:
        logger.error(f"AI Health Monitor Failed: {e}")

async def monitor_system_storage(db: Session):
    """SA006: System Storage Critical"""
    notif_service = get_notification_service(db)
    usage = psutil.disk_usage(settings.UPLOAD_DIR or '/')
    if usage.percent >= 90:
        notif_service.create_storage_critical_notification(
            used=usage.used, 
            total=usage.total, 
            percent=usage.percent
        )

async def monitor_db_performance(db: Session):
    """SA005: Database Performance Alert"""
    # Calculate error rate from system_metrics in the last 10 minutes
    ten_minutes_ago = datetime.utcnow() - timedelta(minutes=10)
    
    total_requests = db.query(func.count(SystemMetric.id)).filter(
        SystemMetric.metric_name == "api_request",
        SystemMetric.created_at >= ten_minutes_ago
    ).scalar() or 0
    
    if total_requests > 10:  # Threshold to avoid noise on low traffic
        # Filter for status codes >= 500 in the JSON details
        error_requests = db.query(func.count(SystemMetric.id)).filter(
            SystemMetric.metric_name == "api_request",
            SystemMetric.created_at >= ten_minutes_ago,
            SystemMetric.details["status"].astext.cast(Integer) >= 500
        ).scalar() or 0
        
        error_rate = error_requests / total_requests
        if error_rate > 0.10:
            notif_service = get_notification_service(db)
            notif_service.create_database_performance_alert_notification(
                error_rate=error_rate,
                details={
                    "query_count": total_requests,
                    "slow_queries": error_requests,
                    "peak_time": datetime.utcnow().isoformat()
                }
            )

async def daily_health_report(db: Session):
    """SA009: System Health Report"""
    notif_service = get_notification_service(db)
    # In a real scenario, this would aggregate actual system_metrics
    notif_service.create_system_health_report_notification(metrics={
        "uptime_percent": 99.9,
        "error_rate": 0.5,
        "active_facilities": 10,
        "active_users": 50
    })

async def run_monitoring_loop():
    """Main background loop for SA004-SA009"""
    while True:
        db = SessionLocal()
        try:
            await monitor_ai_health(db)
            await monitor_system_storage(db)
            
            # Run daily reports only at specific times
            now = datetime.now()
            if now.hour == 8 and now.minute == 0:
                await daily_health_report(db)
                
        except Exception as e:
            logger.error(f"Monitoring Loop Error: {e}")
        finally:
            db.close()
            
        await asyncio.sleep(300) # Check every 5 minutes

def start_monitoring():
    """Startup hook to be called in app/main.py"""
    asyncio.create_task(run_monitoring_loop())