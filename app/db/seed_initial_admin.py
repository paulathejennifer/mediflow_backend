"""
Initial Super Admin Seed Script

This script creates the initial super admin user for the MediFlow system.
It should be run after database migrations to set up the first administrator.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine
from app.models.user import User
from app.enums import UserRole
import bcrypt


def create_initial_super_admin():
    """
    Create the initial super admin user if it doesn't already exist.
    """
    db = SessionLocal()

    try:
        # Check if super admin already exists
        existing_admin = (
            db.query(User).filter(User.email == "admin@mediflow.com").first()
        )

        # Hash the default password using bcrypt directly
        default_password = "admin123"
        # Truncate password to 72 bytes if needed (bcrypt limitation)
        if len(default_password.encode("utf-8")) > 72:
            default_password = default_password[:72]
        hashed_password = bcrypt.hashpw(
            default_password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

        if existing_admin:
            print("✅ Super admin already exists: admin@mediflow.com")
            print(f"   User ID: {existing_admin.id}")
            print(f"   Role: {existing_admin.role}")
            print("⚠️  Existing super admin preserved; no password reset performed.")
            return existing_admin

        # Create the super admin
        super_admin = User(
            first_name="Super",
            last_name="Admin",
            email="admin@mediflow.com",
            phone="+254700000000",
            password_hash=hashed_password,
            role=UserRole.SUPER_ADMIN,
            facility_id=None,  # Super admin doesn't need a facility
            is_active=True,
        )

        db.add(super_admin)
        db.commit()
        db.refresh(super_admin)

        print("✅ Initial super admin created successfully!")
        print(f"   Email: admin@mediflow.com")
        print(f"   Password: {default_password}")
        print(f"   User ID: {super_admin.id}")
        print(f"   Role: {super_admin.role}")
        print("\n⚠️  IMPORTANT: Change the default password after first login!")

        return super_admin

    except Exception as e:
        print(f"❌ Error creating super admin: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


def main():
    """Main entry point for the seed script."""
    print("=" * 60)
    print("MediFlow - Initial Super Admin Setup")
    print("=" * 60)
    print()

    try:
        create_initial_super_admin()
        print()
        print("=" * 60)
        print("Setup completed successfully!")
        print("=" * 60)
    except Exception as e:
        print()
        print("=" * 60)
        print("Setup failed!")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
