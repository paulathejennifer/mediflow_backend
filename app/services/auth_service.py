from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi import HTTPException, status, Depends
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.schemas.auth import UserCreate, UserLogin
from app.core.security import (
    verify_password, get_password_hash, create_access_token,
    create_refresh_token, generate_refresh_token_string, verify_token
)
from app.core.database import get_db
from app.enums import UserRole
from typing import Optional
from datetime import datetime, timedelta

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
        """Login user and return access and refresh tokens."""
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
        
        # Create refresh token
        refresh_token_string = generate_refresh_token_string()
        refresh_token_jwt = create_refresh_token(data={"sub": str(user.id), "token": refresh_token_string})
        
        # Store refresh token in database
        refresh_token = RefreshToken(
            user_id=user.id,
            token=refresh_token_string,
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        self.db.add(refresh_token)
        self.db.commit()
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token_jwt,
            "token_type": "bearer"
        }
    
    def refresh_access_token(self, refresh_token_jwt: str) -> dict:
        """Refresh access token using refresh token."""
        # Verify refresh token JWT
        payload = verify_token(refresh_token_jwt)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Check if it's a refresh token
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        # Get user ID from payload
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Get refresh token string from payload
        refresh_token_string = payload.get("token")
        if not refresh_token_string:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Find refresh token in database
        refresh_token = self.db.query(RefreshToken).filter(
            RefreshToken.token == refresh_token_string,
            RefreshToken.user_id == int(user_id),
            RefreshToken.revoked.is_(None),
            RefreshToken.expires_at > datetime.utcnow()
        ).first()
        
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token not found or expired"
            )
        
        # Get user
        user = self.get_user_by_id(int(user_id))
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Create new access token
        access_token = create_access_token(data={"sub": str(user.id)})
        
        return {
            "access_token": access_token,
            "token_type": "bearer"
        }
    
    def revoke_refresh_token(self, refresh_token_jwt: str) -> bool:
        """Revoke a refresh token."""
        # Verify refresh token JWT
        payload = verify_token(refresh_token_jwt)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Get refresh token string from payload
        refresh_token_string = payload.get("token")
        if not refresh_token_string:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Find and revoke refresh token
        refresh_token = self.db.query(RefreshToken).filter(
            RefreshToken.token == refresh_token_string
        ).first()
        
        if refresh_token:
            refresh_token.revoked = datetime.utcnow()
            self.db.commit()
        
        return True

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

def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    """Get auth service instance."""
    return AuthService(db)
