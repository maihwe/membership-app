"""
Database initialization script.

Creates all tables and loads initial data.
Run this once after deployment to set up the database.

Usage:
    python init_db.py
"""

import os
from datetime import datetime, timedelta
from app import create_app
from models import db, User, Member, ContributionCycle, AuditLog
from config import get_config


def init_database():
    """Create all tables and load initial data."""
    app = create_app()
    
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        print("✓ Tables created")
        
        # Create default super admin if it doesn't exist
        admin = User.query.filter_by(email='admin@membership.local').first()
        if not admin:
            admin = User(
                email='admin@membership.local',
                role='super_admin',
                status='active',
                phone='+234-XXX-XXXX-XXXX'
            )
            db.session.add(admin)
            db.session.commit()
            print(f"✓ Created super admin: {admin.email}")
        
        # Log initialization
        audit = AuditLog(
            user_id=admin.id,
            action='database_initialized',
            resource_type='system',
            resource_id='db',
            status='success'
        )
        db.session.add(audit)
        db.session.commit()
        
        print("\n✓ Database initialization complete")
        print(f"\nDefault super admin: admin@membership.local")
        print("First login: Use 'Request OTP' to get a login code")


if __name__ == '__main__':
    init_database()
