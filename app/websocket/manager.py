"""
WebSocket Connection Manager for MediFlow Notification System

This module handles WebSocket connections for real-time notifications,
including connection management, authentication, and message broadcasting.
"""

import json
import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.notifications import Notification, NotificationDelivery
from app.core.security import verify_token

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and message broadcasting"""
    
    def __init__(self):
        # Store active connections: {user_id: {"websocket": WebSocket, "role": str, "connected_at": datetime}}
        self.active_connections: Dict[str, Dict] = {}
        # Store facility connections for facility-specific broadcasts
        self.facility_connections: Dict[int, List[str]] = {}
        # Store role connections for role-specific broadcasts
        self.role_connections: Dict[str, List[str]] = {}
        
    async def connect(self, websocket: WebSocket, user_id: str, user_role: str, facility_id: Optional[int] = None):
        """Accept and store WebSocket connection"""
        await websocket.accept()
        
        # Close existing connection if user is already connected
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id]["websocket"].close()
                logger.info(f"Closed existing connection for user {user_id}")
            except Exception as e:
                logger.error(f"Error closing existing connection: {e}")
        
        # Store new connection
        self.active_connections[user_id] = {
            "websocket": websocket,
            "role": user_role,
            "facility_id": facility_id,
            "connected_at": datetime.now(timezone.utc),
            "last_ping": datetime.now(timezone.utc)
        }
        
        # Update role connections
        if user_role not in self.role_connections:
            self.role_connections[user_role] = []
        if user_id not in self.role_connections[user_role]:
            self.role_connections[user_role].append(user_id)
        
        # Update facility connections
        if facility_id:
            if facility_id not in self.facility_connections:
                self.facility_connections[facility_id] = []
            if user_id not in self.facility_connections[facility_id]:
                self.facility_connections[facility_id].append(user_id)
        
        logger.info(f"User {user_id} ({user_role}) connected via WebSocket")
        
        # Send pending notifications
        await self.send_pending_notifications(user_id)
    
    async def disconnect(self, user_id: str):
        """Remove WebSocket connection"""
        if user_id in self.active_connections:
            conn_info = self.active_connections[user_id]
            user_role = conn_info["role"]
            facility_id = conn_info["facility_id"]
            
            # Remove from role connections
            if user_role in self.role_connections and user_id in self.role_connections[user_role]:
                self.role_connections[user_role].remove(user_id)
                if not self.role_connections[user_role]:
                    del self.role_connections[user_role]
            
            # Remove from facility connections
            if facility_id and facility_id in self.facility_connections:
                if user_id in self.facility_connections[facility_id]:
                    self.facility_connections[facility_id].remove(user_id)
                if not self.facility_connections[facility_id]:
                    del self.facility_connections[facility_id]
            
            # Remove from active connections
            del self.active_connections[user_id]
            
            logger.info(f"User {user_id} disconnected from WebSocket")
    
    async def send_to_user(self, user_id: str, notification: dict):
        """Send notification to specific user"""
        if user_id in self.active_connections:
            try:
                websocket = self.active_connections[user_id]["websocket"]
                await websocket.send_text(json.dumps(notification))
                logger.info(f"Notification sent to user {user_id}")
                return True
            except Exception as e:
                logger.error(f"Error sending notification to user {user_id}: {e}")
                # Remove broken connection
                await self.disconnect(user_id)
                return False
        else:
            logger.warning(f"User {user_id} not connected")
            return False
    
    async def broadcast_to_role(self, role: str, notification: dict):
        """Broadcast notification to all users with specific role"""
        if role in self.role_connections:
            success_count = 0
            failed_count = 0
            
            for user_id in self.role_connections[role][:]:  # Use slice to avoid modification during iteration
                if await self.send_to_user(user_id, notification):
                    success_count += 1
                else:
                    failed_count += 1
            
            logger.info(f"Broadcast to role {role}: {success_count} sent, {failed_count} failed")
            return success_count, failed_count
        else:
            logger.warning(f"No users connected with role {role}")
            return 0, 0
    
    async def broadcast_to_roles(self, roles: List[str], notification: dict):
        """Broadcast notification to multiple roles"""
        total_sent = 0
        total_failed = 0
        
        for role in roles:
            sent, failed = await self.broadcast_to_role(role, notification)
            total_sent += sent
            total_failed += failed
        
        logger.info(f"Broadcast to roles {roles}: {total_sent} sent, {total_failed} failed")
        return total_sent, total_failed
    
    async def broadcast_to_facility(self, facility_id: int, notification: dict):
        """Broadcast notification to all users in specific facility"""
        if facility_id in self.facility_connections:
            success_count = 0
            failed_count = 0
            
            for user_id in self.facility_connections[facility_id][:]:
                if await self.send_to_user(user_id, notification):
                    success_count += 1
                else:
                    failed_count += 1
            
            logger.info(f"Broadcast to facility {facility_id}: {success_count} sent, {failed_count} failed")
            return success_count, failed_count
        else:
            logger.warning(f"No users connected to facility {facility_id}")
            return 0, 0
    
    async def send_pending_notifications(self, user_id: int):
        """Send pending notifications to newly connected user"""
        try:
            # Get database session
            db = next(get_db())
            
            # Get undelivered notifications for this user
            undelivered_notifications = db.query(Notification).filter(
                Notification.user_id == user_id,
                Notification.is_read == False
            ).order_by(Notification.created_at.desc()).limit(50).all()
            
            for notification in undelivered_notifications:
                notification_data = {
                    "id": notification.id,
                    "type": notification.notification_type,
                    "title": notification.title,
                    "message": notification.message,
                    "details": notification.details,
                    "actions": notification.actions,
                    "roles": notification.roles,
                    "backend_source": notification.backend_source,
                    "timestamp": notification.created_at.isoformat(),
                    "expires_at": notification.expires_at.isoformat() if notification.expires_at else None
                }
                
                await self.send_to_user(str(user_id), notification_data)
                
                # Mark as delivered via WebSocket
                delivery = NotificationDelivery(
                    notification_id=notification.id,
                    user_id=user_id,
                    delivery_method="websocket",
                    delivered_at=datetime.now(timezone.utc),
                    delivery_status="delivered"
                )
                db.add(delivery)
            
            db.commit()
            db.close()
            
            logger.info(f"Sent {len(undelivered_notifications)} pending notifications to user {user_id}")
            
        except Exception as e:
            logger.error(f"Error sending pending notifications to user {user_id}: {e}")
    
    async def ping_all_connections(self):
        """Ping all connections to check if they're still alive"""
        current_time = datetime.now(timezone.utc)
        dead_connections = []
        
        for user_id, conn_info in self.active_connections.items():
            # Check if connection is too old (no ping for 5 minutes)
            if (current_time - conn_info["last_ping"]).seconds > 300:
                dead_connections.append(user_id)
                continue
            
            try:
                websocket = conn_info["websocket"]
                await websocket.ping()
                conn_info["last_ping"] = current_time
            except Exception as e:
                logger.error(f"Ping failed for user {user_id}: {e}")
                dead_connections.append(user_id)
        
        # Remove dead connections
        for user_id in dead_connections:
            await self.disconnect(user_id)
        
        if dead_connections:
            logger.info(f"Removed {len(dead_connections)} dead connections")
    
    def get_connection_stats(self) -> Dict:
        """Get statistics about current connections"""
        role_stats = {}
        for role, users in self.role_connections.items():
            role_stats[role] = len(users)
        
        facility_stats = {}
        for facility_id, users in self.facility_connections.items():
            facility_stats[facility_id] = len(users)
        
        return {
            "total_connections": len(self.active_connections),
            "role_distribution": role_stats,
            "facility_distribution": facility_stats,
            "connected_users": list(self.active_connections.keys())
        }


class NotificationBroadcaster:
    """Handles notification broadcasting logic"""
    
    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager
    
    async def broadcast_notification(self, notification: Notification, db: Session):
        """Broadcast notification to appropriate users based on roles and facility"""
        notification_data = {
            "id": notification.id,
            "type": notification.notification_type,
            "title": notification.title,
            "message": notification.message,
            "details": notification.details,
            "actions": notification.actions,
            "roles": notification.roles,
            "backend_source": notification.backend_source,
            "timestamp": notification.created_at.isoformat(),
            "expires_at": notification.expires_at.isoformat() if notification.expires_at else None
        }
        
        # Determine target users based on roles
        target_roles = notification.roles
        
        # Handle shared notifications (roles include both "facility_admin" and "clinician")
        if "shared" in target_roles:
            target_roles = ["facility_admin", "clinician"]
        
        # Broadcast to target roles
        total_sent, total_failed = await self.connection_manager.broadcast_to_roles(
            target_roles, notification_data
        )
        
        # If notification is facility-specific, also broadcast to facility users
        if hasattr(notification, 'facility_id') and notification.facility_id:
            facility_sent, facility_failed = await self.connection_manager.broadcast_to_facility(
                notification.facility_id, notification_data
            )
            total_sent += facility_sent
            total_failed += facility_failed
        
        # Record delivery attempts
        await self.record_delivery_attempts(notification, target_roles, total_sent, total_failed, db)
        
        logger.info(f"Notification {notification.id} broadcast: {total_sent} sent, {total_failed} failed")
        
        return total_sent, total_failed
    
    async def record_delivery_attempts(self, notification: Notification, target_roles: List[str], 
                                      sent_count: int, failed_count: int, db: Session):
        """Record notification delivery attempts"""
        try:
            # Get all users with target roles
            from app.models.user import User
            target_users = db.query(User).filter(User.role.in_(target_roles)).all()
            
            for user in target_users:
                delivery_status = "delivered" if sent_count > 0 else "failed"
                
                # Check if user was actually connected
                if str(user.id) in self.connection_manager.active_connections:
                    delivery_status = "delivered"
                else:
                    delivery_status = "pending"  # Will be delivered when user connects
                
                delivery = NotificationDelivery(
                    notification_id=notification.id,
                    user_id=user.id,
                    delivery_method="websocket",
                    delivery_status=delivery_status,
                    delivered_at=datetime.now(timezone.utc) if delivery_status == "delivered" else None
                )
                db.add(delivery)
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Error recording delivery attempts: {e}")
            db.rollback()


# Global connection manager instance
connection_manager = ConnectionManager()
notification_broadcaster = NotificationBroadcaster(connection_manager)


async def authenticate_websocket(token: str, db: Session) -> Optional[User]:
    """Authenticate WebSocket connection using JWT token"""
    try:
        payload = verify_token(token)
        user_id = payload.get("sub")
        
        if not user_id:
            return None
        
        user = db.query(User).filter(User.id == int(user_id)).first()
        
        if not user or not user.is_active:
            return None
        
        return user
        
    except Exception as e:
        logger.error(f"WebSocket authentication error: {e}")
        return None


async def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager instance"""
    return connection_manager


async def get_notification_broadcaster() -> NotificationBroadcaster:
    """Get the global notification broadcaster instance"""
    return notification_broadcaster
