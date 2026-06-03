"""
User Service for Mediflow System

This service handles user-related business logic including:
- User creation and management
- Role-based operations
- Facility assignment
- User activity tracking
"""

from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from fastapi import HTTPException, status
from app.models.user import User
from app.models.facility import Facility
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash
from app.enums import UserRole
from app.utils.audit_utils import create_audit_logger
from app.enums import AuditAction
from typing import List, Optional


def normalize_email(email: str) -> str:
    if isinstance(email, str):
        return email.strip().lower()
    return email



class UserService:
    """Service for user management operations."""

    def __init__(self, db: Session):
        self.db = db

    def create_user(self, user_data: UserCreate, creator_id: int) -> User:
        """
        Create a new user with validation and role checks.

        Args:
            user_data: User creation data
            creator_id: ID of user creating this user

        Returns:
            Created user object
        """
        email = normalize_email(user_data.email)
        # Check if email already exists
        existing_user = (
            self.db.query(User).filter(User.email == email).first()
        )
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        # Validate role
        if user_data.role not in [role.value for role in UserRole]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role. Must be one of: {[role.value for role in UserRole]}",
            )

        # Validate facility assignment for non-super admins
        if user_data.role != UserRole.SUPER_ADMIN.value and not user_data.facility_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Facility assignment required for this role",
            )

        # Verify facility exists if assigned
        if user_data.facility_id:
            facility = (
                self.db.query(Facility)
                .filter(Facility.id == user_data.facility_id)
                .first()
            )
            if not facility:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Assigned facility not found",
                )

        # Create user
        user = User(
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            email=email,
            password_hash=get_password_hash(user_data.password),
            role=user_data.role,
            phone=user_data.phone,
            gender=user_data.gender,
            facility_id=user_data.facility_id,
        )

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        # Log the action so it appears in API Request analytics
        audit_logger = create_audit_logger(self.db)
        audit_logger.log_action(
            user_id=creator_id,
            action=AuditAction.CREATE.value,
            entity_type="user",
            entity_id=user.id,
            details={"email": user.email, "role": user.role}
        )

        return user

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return self.db.query(User).filter(User.id == user_id).first()

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return self.db.query(User).filter(User.email == normalize_email(email)).first()

    def update_user(
        self, user_id: int, user_update: UserUpdate, updater_id: int
    ) -> User:
        """
        Update user information with validation.

        Args:
            user_id: ID of user to update
            user_update: Update data
            updater_id: ID of user performing update

        Returns:
            Updated user object
        """
        user = self.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        update_data = user_update.dict(exclude_unset=True)

        # Normalize and validate email uniqueness if being updated
        if "email" in update_data:
            update_data["email"] = normalize_email(update_data["email"])
            existing_user = (
                self.db.query(User)
                .filter(and_(User.email == update_data["email"], User.id != user_id))
                .first()
            )
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered",
                )

        # Validate role if being updated
        if "role" in update_data:
            if update_data["role"] not in [role.value for role in UserRole]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid role. Must be one of: {[role.value for role in UserRole]}",
                )

        # Validate facility assignment if being updated
        if "facility_id" in update_data and update_data["facility_id"]:
            facility = (
                self.db.query(Facility)
                .filter(Facility.id == update_data["facility_id"])
                .first()
            )
            if not facility:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Assigned facility not found",
                )

        # Apply updates
        for field, value in update_data.items():
            setattr(user, field, value)

        self.db.commit()
        self.db.refresh(user)

        return user

    def deactivate_user(self, user_id: int, deactivator_id: int) -> User:
        """
        Deactivate user account.

        Args:
            user_id: ID of user to deactivate
            deactivator_id: ID of user performing deactivation

        Returns:
            Deactivated user object
        """
        user = self.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already deactivated",
            )

        user.is_active = False
        self.db.commit()
        self.db.refresh(user)

        return user

    def activate_user(self, user_id: int, activator_id: int) -> User:
        """
        Activate user account.

        Args:
            user_id: ID of user to activate
            activator_id: ID of user performing activation

        Returns:
            Activated user object
        """
        user = self.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        if user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="User is already active"
            )

        user.is_active = True
        self.db.commit()
        self.db.refresh(user)

        return user

    def list_facility_users(
        self, facility_id: int, skip: int = 0, limit: int = 100
    ) -> List[User]:
        """
        List users in a specific facility.

        Args:
            facility_id: Facility ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of users in the facility
        """
        return (
            self.db.query(User)
            .filter(User.facility_id == facility_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def list_users_by_role(
        self, role: str, skip: int = 0, limit: int = 100
    ) -> List[User]:
        """
        List users by role.

        Args:
            role: User role to filter by
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of users with specified role
        """
        return (
            self.db.query(User)
            .filter(User.role == role)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_user_stats(self, facility_id: Optional[int] = None) -> dict:
        """
        Get user statistics.

        Args:
            facility_id: Optional facility ID to filter by

        Returns:
            Dictionary with user statistics
        """
        query = self.db.query(User)

        if facility_id:
            query = query.filter(User.facility_id == facility_id)

        total_users = query.count()
        active_users = query.filter(User.is_active == True).count()

        # Count by role
        role_stats = {}
        for role in UserRole:
            role_count = query.filter(User.role == role.value).count()
            role_stats[role.value] = role_count

        return {
            "total_users": total_users,
            "active_users": active_users,
            "inactive_users": total_users - active_users,
            "role_breakdown": role_stats,
        }


def get_user_service(db: Session) -> UserService:
    """Get user service instance."""
    return UserService(db)
