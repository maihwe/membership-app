"""
Authentication routes - OTP request, verification, logout.
"""

from flask import Blueprint, request, jsonify, render_template, g, make_response
from auth import (
    OTPManager, SessionManager, require_session,
    AuthError, _get_client_ip
)
from models import db, User, AuditLog

bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@bp.route('/request-code', methods=['POST'])
def request_otp_code():
    """
    Request an OTP code for login.
    
    POST /api/auth/request-code
    {
        "email": "user@example.com"
    }
    
    Returns:
    {
        "request_id": "...",
        "expires_minutes": 10,
        "message": "OTP sent to email"
    }
    """
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    
    if not email:
        return jsonify({'error': 'Email is required'}), 400
    
    # Validate email format
    if '@' not in email or '.' not in email:
        return jsonify({'error': 'Invalid email format'}), 400
    
    try:
        result = OTPManager.request_code(email)
        return jsonify(result), 200
    except AuthError as e:
        return jsonify({'error': e.message}), e.code
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error: {str(e)}'}), 500


@bp.route('/verify', methods=['POST'])
def verify_otp_code():
    """
    Verify OTP code and create session.
    
    POST /api/auth/verify
    {
        "email": "user@example.com",
        "code": "123456",
        "request_id": "..."
    }
    
    Returns:
    {
        "ok": True,
        "token": "...",
        "expires_at": 1234567890,
        "user": {...}
    }
    """
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    code = data.get('code', '').strip()
    request_id = data.get('request_id', '').strip()
    
    if not all([email, code, request_id]):
        return jsonify({'error': 'Email, code, and request_id are required'}), 400
    
    try:
        result = OTPManager.verify_code(email, code, request_id)
        
        # Set secure cookie for web sessions
        response = make_response(jsonify(result))
        response.set_cookie(
            'session_token',
            result['token'],
            max_age=12*3600,  # 12 hours
            secure=True,
            httponly=True,
            samesite='Lax'
        )
        
        return response, 200
    except AuthError as e:
        return jsonify({'error': e.message}), e.code
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error: {str(e)}'}), 500


@bp.route('/logout', methods=['POST'])
@require_session
def logout():
    """
    Logout current user and invalidate session.
    
    POST /api/auth/logout
    Headers: Authorization: Bearer <token>
    
    Returns:
    {
        "ok": True,
        "message": "Logged out"
    }
    """
    try:
        token = g.token
        user = g.user
        
        SessionManager.logout(token)
        
        # Log logout
        audit = AuditLog(
            user_id=user.id,
            action='logout',
            resource_type='user',
            resource_id=user.id,
            ip_address=_get_client_ip(),
            status='success'
        )
        db.session.add(audit)
        db.session.commit()
        
        response = make_response(jsonify({
            'ok': True,
            'message': 'Logged out successfully'
        }))
        response.delete_cookie('session_token')
        
        return response, 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error: {str(e)}'}), 500


@bp.route('/me', methods=['GET'])
@require_session
def get_current_user():
    """
    Get current authenticated user.
    
    GET /api/auth/me
    Headers: Authorization: Bearer <token>
    
    Returns:
    {
        "id": "...",
        "email": "...",
        "role": "...",
        "status": "...",
        "last_login_at": "..."
    }
    """
    user = g.user
    return jsonify({
        'id': user.id,
        'email': user.email,
        'role': user.role,
        'status': user.status,
        'phone': user.phone,
        'last_login_at': user.last_login_at.isoformat() if user.last_login_at else None,
    }), 200


@bp.route('/status', methods=['GET'])
def check_status():
    """Health check endpoint."""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.utcnow().isoformat()
    }), 200


# HTML/Form-based auth (for traditional web interface)

@bp.route('/login', methods=['GET'])
def login_page():
    """Render login page."""
    return render_template('auth/login.html')


@bp.route('/verify', methods=['GET'])
def verify_page():
    """Render OTP verification page."""
    return render_template('auth/verify.html')
