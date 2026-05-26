"""
WebSocket API endpoints for MediFlow Notification System

This module provides WebSocket endpoints for real-time notifications
and related API endpoints for notification management.
"""

import logging
from typing import Optional
from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
    Query,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.websocket.manager import connection_manager, authenticate_websocket
from app.services.notification_service import get_notification_service
from app.models.user import User
from app.models.notifications import Notification

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/notifications")
async def websocket_notifications(
    websocket: WebSocket, token: str = Query(...), db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for real-time notifications

    Parameters:
    - token: JWT authentication token
    - db: Database session
    """

    # Authenticate user
    user = await authenticate_websocket(token, db)
    if not user:
        await websocket.close(code=4001, reason="Authentication failed")
        return

    # Get user facility ID
    facility_id = user.facility_id if hasattr(user, "facility_id") else None

    try:
        # Connect to WebSocket manager
        await connection_manager.connect(
            websocket=websocket,
            user_id=str(user.id),
            user_role=user.role,
            facility_id=facility_id,
        )

        logger.info(f"User {user.id} ({user.role}) connected to WebSocket")

        # Keep connection alive and handle messages
        while True:
            try:
                # Receive message (could be ping, pong, or other client messages)
                message = await websocket.receive_text()

                # Handle client messages if needed
                if message == "ping":
                    await websocket.send_text("pong")
                elif message == "get_stats":
                    # Send connection stats
                    stats = connection_manager.get_connection_stats()
                    await websocket.send_text(f"stats:{stats}")

            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error receiving WebSocket message: {e}")
                break

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user {user.id}")
    except Exception as e:
        logger.error(f"WebSocket error for user {user.id}: {e}")
    finally:
        # Clean up connection
        await connection_manager.disconnect(str(user.id))


@router.get("/notifications/system-stats")
async def get_system_notification_stats(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Get system-wide notification statistics (Super Admin only)

    Parameters:
    - current_user: Authenticated user
    - db: Database session
    """

    if current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Super Admin required.",
        )

    # Get system stats
    connection_stats = connection_manager.get_connection_stats()

    # Get notification stats from database
    from sqlalchemy import func

    total_notifications = db.query(Notification).count()
    unread_notifications = (
        db.query(Notification).filter(Notification.is_read == False).count()
    )

    critical_notifications = (
        db.query(Notification)
        .filter(Notification.notification_type == "critical")
        .count()
    )

    warning_notifications = (
        db.query(Notification)
        .filter(Notification.notification_type == "warning")
        .count()
    )

    info_notifications = (
        db.query(Notification).filter(Notification.notification_type == "info").count()
    )

    return {
        "connections": connection_stats,
        "notifications": {
            "total": total_notifications,
            "unread": unread_notifications,
            "critical": critical_notifications,
            "warning": warning_notifications,
            "info": info_notifications,
        },
    }


@router.post("/notifications/test")
async def create_test_notification(
    notification_type: str = "info",
    title: str = "Test Notification",
    message: str = "This is a test notification",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a test notification (for development/testing)

    Parameters:
    - notification_type: Type of notification (critical, warning, info)
    - title: Notification title
    - message: Notification message
    - current_user: Authenticated user
    - db: Database session
    """

    notification_service = get_notification_service(db)

    # Determine roles based on user role
    if current_user.role == "super_admin":
        roles = ["super_admin"]
    elif current_user.role == "facility_admin":
        roles = ["facility_admin", "clinician"]  # Shared
    else:  # clinician
        roles = ["clinician"]

    notification = notification_service.create_notification(
        notification_type=notification_type,
        title=title,
        message=message,
        details={"test": True, "created_by": current_user.id},
        actions=["📋 View Details", "✅ Dismiss"],
        roles=roles,
        backend_source="test",
    )

    return {"message": "Test notification created", "notification_id": notification.id}
