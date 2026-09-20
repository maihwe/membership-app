"""
Flask application factory and configuration.

Creates and configures the Flask app with:
- Database initialization
- Blueprint registration
- Error handlers
- Request/response middleware
"""
import logging
import logging.handlers
from flask import Flask, jsonify, render_template, request
from datetime import datetime
import logging
import os
from config import get_config
from models import db


def create_app(config=None):
    """
    Create and configure Flask application.
    
    Args:
        config: Config object (uses FLASK_ENV if not provided)
    
    Returns:
        Flask app instance
    """
    app = Flask(__name__)
    
    # Load configuration
    if config is None:
        config = get_config()
    app.config.from_object(config)
    
    # Initialize extensions
    db.init_app(app)
    
    # Setup logging
    _setup_logging(app)
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    # Register blueprints (routes)
    _register_blueprints(app)
    
    # Register error handlers
    _register_error_handlers(app)
    
    # Register middleware/hooks
    _register_middleware(app)
    
    return app


def _setup_logging(app):
    """Configure application logging."""
    os.makedirs('logs', exist_ok=True)
    
    if not app.debug:
        
        file_handler = logging.handlers.RotatingFileHandler(
            'logs/membership.log',
            maxBytes=10240,
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
    
    app.logger.setLevel(logging.INFO)
    app.logger.info('Membership app startup')


def _register_blueprints(app):
    """Register route blueprints."""
    import routes_auth as auth_routes
    import routes_members as members_routes
    import routes_contributions as contributions_routes
    import routes_loans as loans_routes
    import routes_payments as payments_routes
    import routes_messages as messages_routes
    import routes_admin as admin_routes
    
    app.register_blueprint(auth_routes.bp)
    app.register_blueprint(members_routes.bp)
    app.register_blueprint(contributions_routes.bp)
    app.register_blueprint(loans_routes.bp)
    app.register_blueprint(payments_routes.bp)
    app.register_blueprint(messages_routes.bp)
    app.register_blueprint(admin_routes.bp)
    
    # Home route
    @app.route('/')
    def index():
        return render_template('index.html')
    
    @app.route('/api/health', methods=['GET'])
    def health():
        return jsonify({'status': 'ok', 'timestamp': datetime.utcnow().isoformat()}), 200


def _register_error_handlers(app):
    """Register global error handlers."""
    
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({'error': 'Bad request'}), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({'error': 'Unauthorized'}), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({'error': 'Forbidden'}), 403
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        app.logger.error(f'Internal error: {error}')
        return jsonify({'error': 'Internal server error'}), 500
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        app.logger.error(f'Unhandled exception: {error}')
        return jsonify({'error': 'An error occurred'}), 500


def _register_middleware(app):
    """Register request/response middleware."""
    
    @app.before_request
    def log_request():
        """Log incoming request."""
        if request.path.startswith('/static'):
            return
        app.logger.debug(f"{request.method} {request.path}")
    
    @app.after_request
    def add_headers(response):
        """Add security headers."""
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
