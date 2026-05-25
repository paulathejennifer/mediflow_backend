"""
Notification API Endpoints

This module provides REST endpoints for notification management, including
listing, marking as read, and handling interactive actions.
"""

import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.notification_service import get_notification_service

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/", response_model=List[Dict[str, Any]])
async def list_notifications(
    notification_type: Optional[str] = None,
    unread_only: bool = False,
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get user notifications.
    Returns a list of notifications matching the criteria.
    """
    service = get_notification_service(db)
    notifications = service.get_user_notifications(
        user_id=current_user.id,
        user_role=current_user.role,
        notification_type=notification_type,
        unread_only=unread_only,
        limit=limit
    )
    
    # Format for frontend Notification interface
    return [
        {
            "id": n.id,
            "type": n.notification_type,
            "title": n.title,
            "message": n.message,
            "details": n.details,
            "actions": n.actions,
            "backend_source": n.backend_source,
            "created_at": n.created_at.isoformat(),
            "is_read": n.is_read,
        } for n in notifications
    ]

@router.patch("/{notification_id}/read")
async def mark_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a specific notification as read."""
    service = get_notification_service(db)
    if service.mark_notification_read(notification_id, current_user.id):
        return {"status": "success"}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

@router.patch("/read-all")
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark all unread notifications for the user as read."""
    service = get_notification_service(db)
    count = service.mark_all_as_read(current_user.id, current_user.role)
    return {"status": "success", "count": count}

@router.post("/{notification_id}/actions/{action_id}")
async def handle_action(
    notification_id: int,
    action_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Unified handler for notification action buttons."""
    service = get_notification_service(db)
    return service.handle_notification_action(notification_id, current_user.id, action_id)

@router.get("/stats")
async def get_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get notification statistics for the current user."""
    service = get_notification_service(db)
    return service.get_notification_stats(current_user.id, current_user.role)
