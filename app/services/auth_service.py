from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi import HTTPException, status
from app.models.user import User
from app.schemas.auth import UserCreate, UserLogin
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.database import get_db
from app.enums import UserRole
from typing import Optional
from datetime import timedelta

class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password."""
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    def create_user(self, user_data: UserCreate) -> User:
        """Create a new user."""
        # Check if user already exists
        existing_user = self.db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Validate role
        if user_data.role not in [role.value for role in UserRole]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role. Must be one of: {[role.value for role in UserRole]}"
            )
        
        # Hash password
        password_hash = get_password_hash(user_data.password)
        
        # Create user
        user = User(
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            email=user_data.email,
            password_hash=password_hash,
            role=user_data.role,
            facility_id=user_data.facility_id
        )
        
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        return user

    def login_user(self, login_data: UserLogin) -> dict:
        """Login user and return access token."""
        user = self.authenticate_user(login_data.email, login_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User account is inactive"
            )
        
        # Create access token
        access_token = create_access_token(data={"sub": str(user.id)})
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.role,
                "facility_id": user.facility_id
            }
        }

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return self.db.query(User).filter(User.id == user_id).first()

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return self.db.query(User).filter(User.email == email).first()

    def update_user_password(self, user_id: int, current_password: str, new_password: str) -> bool:
        """Update user password."""
        user = self.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Verify current password
        if not verify_password(current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Update password
        user.password_hash = get_password_hash(new_password)
        self.db.commit()
        
        return True

    def deactivate_user(self, user_id: int) -> bool:
        """Deactivate user account."""
        user = self.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user.is_active = False
        self.db.commit()
        
        return True

    def activate_user(self, user_id: int) -> bool:
        """Activate user account."""
        user = self.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user.is_active = True
        self.db.commit()
        
        return True

def get_auth_service(db: Session = None) -> AuthService:
    """Get auth service instance."""
    if db is None:
        db = next(get_db())
    return AuthService(db)
