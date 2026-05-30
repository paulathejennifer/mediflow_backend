from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    facility_id = Column(Integer, ForeignKey("facilities.id"), nullable=True)
    notification_type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    details = Column(JSON, default={})
    actions = Column(JSON, default=[])
    roles = Column(JSON, default=[])
    backend_source = Column(String, default="system")
    trigger_condition = Column(Text, nullable=True)
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    deliveries = relationship("NotificationDelivery", back_populates="notification")

    def __repr__(self):
        return f"<Notification(id={self.id}, type={self.notification_type}, title={self.title})>"


class NotificationDelivery(Base):
    __tablename__ = "notification_deliveries"

    id = Column(Integer, primary_key=True, index=True)
    notification_id = Column(Integer, ForeignKey("notifications.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    delivery_method = Column(String, default="websocket")
    delivery_status = Column(String, default="pending")
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    action_taken = Column(String, nullable=True)
    action_result = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    notification = relationship("Notification", back_populates="deliveries")

    def __repr__(self):
        return f"<NotificationDelivery(id={self.id}, notification_id={self.notification_id})>"


class NotificationTemplate(Base):
    __tablename__ = "notification_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    notification_type = Column(String, nullable=False)
    title_template = Column(String, nullable=False)
    message_template = Column(Text, nullable=False)
    default_roles = Column(JSON, default=[])
    backend_source = Column(String, default="system")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<NotificationTemplate(id={self.id}, name={self.name})>"


class SystemMetric(Base):
    __tablename__ = "system_metrics"

    id = Column(Integer, primary_key=True, index=True)
    metric_name = Column(String, nullable=False)
    metric_value = Column(String, nullable=True)
    details = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<SystemMetric(id={self.id}, name={self.metric_name})>"


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    notification_type = Column(String, nullable=False)
    enabled = Column(Boolean, default=True)
    delivery_methods = Column(JSON, default=["websocket"])
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<NotificationPreference(id={self.id}, user_id={self.user_id})>"


class NotificationQueue(Base):
    __tablename__ = "notification_queue"

    id = Column(Integer, primary_key=True, index=True)
    notification_id = Column(Integer, ForeignKey("notifications.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, default="pending")
    attempts = Column(Integer, default=0)
    last_attempt_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<NotificationQueue(id={self.id}, status={self.status})>"
