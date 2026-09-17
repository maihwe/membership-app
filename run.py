"""
Application entry point.

Usage:
    python run.py
    
Then open http://localhost:5000 in your browser.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import create_app - updated import path
from app_updated import create_app

# Create app instance (for gunicorn)
app = create_app()

# Ensure required folders exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('logs', exist_ok=True)

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    
    print(f"\n{'='*60}")
    print(f"Membership Management System")
    print(f"{'='*60}")
    print(f"Environment: {os.getenv('FLASK_ENV', 'development')}")
    print(f"Database: {app.config.get('SQLALCHEMY_DATABASE_URI')}")
    print(f"Starting on http://localhost:{port}")
    print(f"{'='*60}\n")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
