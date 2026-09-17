"""
Configuration management for the membership app.
Loads from environment variables (.env file).
"""

import os
from datetime import timedelta


class Config:
    """Base configuration - shared by all environments."""
    
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
    DEBUG = False
    TESTING = False
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'sqlite:///membership.db'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    
    # Session & Security
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_DURATION = timedelta(days=7)
    REMEMBER_COOKIE_HTTPONLY = True
    
    # Email Configuration
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', True)
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@membership.local')
    
    # Email Backend (for testing)
    # Set to 'console' in development to print emails to stdout
    MAIL_BACKEND = os.getenv('MAIL_BACKEND', 'smtp')
    
    # OTP Settings
    OTP_LENGTH = 6
    OTP_EXPIRY_MINUTES = 10
    OTP_MAX_ATTEMPTS = 3
    OTP_RATE_LIMIT_HOURS = 1
    OTP_RATE_LIMIT_PER_HOUR = 5
    
    # Session Settings
    SESSION_EXPIRY_HOURS = 12
    SESSION_TOKEN_LENGTH = 32
    
    # Organization Settings
    ORG_NAME = os.getenv('ORG_NAME', 'Membership Organization')
    ORG_EMAIL = os.getenv('ORG_EMAIL', 'noreply@membership.local')
    ORG_PHONE = os.getenv('ORG_PHONE', '')
    ORG_ADDRESS = os.getenv('ORG_ADDRESS', '')
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    # Pagination
    ITEMS_PER_PAGE = 20
    
    # Upload Settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max file upload
    UPLOAD_FOLDER = 'uploads'
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'jpg', 'jpeg', 'png', 'gif'}
    
    # Contribution Settings
    PENALTY_PERCENTAGE = 10  # 10% penalty for late payments
    PENALTY_DAYS_THRESHOLD = 7  # Days after due date before penalty applies


class DevelopmentConfig(Config):
    """Development environment configuration."""
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    MAIL_BACKEND = 'console'
    SQLALCHEMY_ECHO = True


class TestingConfig(Config):
    """Testing environment configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    """Production environment configuration."""
    DEBUG = False
    SESSION_COOKIE_SECURE = True


def get_config(env=None):
    """Get configuration based on environment."""
    env = env or os.getenv('FLASK_ENV', 'development')
    
    config_map = {
        'development': DevelopmentConfig,
        'testing': TestingConfig,
        'production': ProductionConfig,
    }
    
    return config_map.get(env, DevelopmentConfig)
