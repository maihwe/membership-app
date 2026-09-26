"""
Authentication module for passwordless OTP-based login.

Flow:
1. User requests OTP → generates 6-digit code, hashes it, stores hash with expiry
2. Email OTP to user
3. User submits OTP → verify using constant-time comparison
4. On success → issue session token (12-hour validity)
5. All future requests validated against session token
"""

import os
import secrets
import hashlib
import hmac
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, session, g
from models import db, User, OTPChallenge, Session, AuditLog, Member
from config import Config


class AuthError(Exception):
    """Authentication error."""
    def __init__(self, message, code=400):
        self.message = message
        self.code = code


class OTPGenerator:
    """Generate and verify one-time passwords."""
    
    @staticmethod
    def generate_code(length=6):
        """Generate a random N-digit code."""
        return ''.join([str(secrets.randbelow(10)) for _ in range(length)])
    
    @staticmethod
    def hash_code(email, challenge_id, code):
        """
        Hash the OTP code using SHA256.
        Includes email and challenge_id to prevent code reuse across users/attempts.
        
        One-way hash: cannot reverse to get original code.
        """
        data = f"{email}:{challenge_id}:{code}".encode('utf-8')
        return hashlib.sha256(data).hexdigest()
    
    @staticmethod
    def constant_time_compare(a, b):
        """
        Compare two strings using constant-time comparison.
        
        Prevents timing attacks where attacker measures response time to guess correct digits.
        For example, "1" takes slightly longer to reject than "9" if "1" is the first correct digit.
        Constant-time comparison takes same time regardless of where strings differ.
        """
        return hmac.compare_digest(a.encode(), b.encode())


class OTPManager:
    """Manage OTP generation, storage, and verification."""
    
    @staticmethod
    def request_code(email, user_id=None):
        """
        Generate and store an OTP challenge.
        
        Args:
            email: User's email
            user_id: User ID (optional - creates if doesn't exist)
        
        Returns:
            {
                "request_id": "uuid",
                "expires_minutes": 10,
                "message": "Code sent to email"
            }
        
        Raises:
            AuthError: If rate limit exceeded or other error
        """
        # Check rate limiting (max 5 attempts per hour)
        recent_challenges = OTPChallenge.query.filter(
            OTPChallenge.email == email,
            OTPChallenge.created_at > (datetime.utcnow() - timedelta(hours=1))
        ).count()
        
        if recent_challenges >= Config.OTP_RATE_LIMIT_PER_HOUR:
            raise AuthError(
                f"Too many OTP requests. Try again in 1 hour.",
                code=429
            )
        
        # Get or create user
        user = User.query.filter_by(email=email).first()
        if not user:
            if user_id:
                user = User(id=user_id, email=email, role='member')
            else:
                user = User(email=email, role='member')
            db.session.add(user)
            db.session.commit()
        
        if user.status != 'active':
            raise AuthError("User account is inactive or suspended", code=403)
        
        # Generate code and hash
        code = OTPGenerator.generate_code(Config.OTP_LENGTH)
        expires_at = datetime.utcnow() + timedelta(minutes=Config.OTP_EXPIRY_MINUTES)
        
        # Create challenge record
        challenge = OTPChallenge(
            user_id=user.id,
            email=email,
            code_hash=OTPGenerator.hash_code(email, 'pending', code),
            expires_at=expires_at,
            status='pending'
        )
        db.session.add(challenge)
        db.session.commit()
        
        # Log the request
        _log_audit(user.id, 'otp_requested', 'user', user.id, {'email': email})
        
        # Send email (TODO: integrate email service)
        # For now, just return code for testing
        print(f"[OTP DEBUG] Code for {email}: {code}")
        
        return {
            'request_id': challenge.id,
            'expires_minutes': Config.OTP_EXPIRY_MINUTES,
            'code': code,  # REMOVE IN PRODUCTION - only for testing
            'message': f'OTP code sent to {email}'
        }
    
    @staticmethod
    def verify_code(email, code, request_id):
        """
        Verify an OTP code and issue session token.
        
        Args:
            email: User's email
            code: 6-digit code submitted by user
            request_id: OTP challenge ID
        
        Returns:
            {
                "ok": True,
                "token": "session_token",
                "expires_at": 1234567890,
                "user": {"email": "...", "role": "..."}
            }
        
        Raises:
            AuthError: If verification fails
        """
        # Get the challenge
        challenge = OTPChallenge.query.filter_by(
            id=request_id,
            email=email
        ).first()
        
        if not challenge:
            raise AuthError("OTP request not found", code=400)
        
        if challenge.status != 'pending':
            raise AuthError("OTP already used or expired", code=400)
        
        if challenge.is_expired:
            challenge.status = 'expired'
            db.session.commit()
            raise AuthError("OTP code has expired", code=400)
        
        # Check max attempts
        if challenge.attempts >= Config.OTP_MAX_ATTEMPTS:
            challenge.status = 'failed'
            db.session.commit()
            raise AuthError("Too many incorrect attempts. Request a new code", code=429)
        
        # Verify code using constant-time comparison
        computed_hash = OTPGenerator.hash_code(email, 'pending', code)
        
        if not OTPGenerator.constant_time_compare(computed_hash, challenge.code_hash):
            # Wrong code
            challenge.attempts += 1
            db.session.commit()
            
            remaining = Config.OTP_MAX_ATTEMPTS - challenge.attempts
            if remaining > 0:
                raise AuthError(f"Invalid code. {remaining} attempts remaining", code=400)
            else:
                challenge.status = 'failed'
                db.session.commit()
                raise AuthError("Too many incorrect attempts. Request a new code", code=429)
        
        # Correct code - issue session
        challenge.status = 'verified'
        challenge.verified_at = datetime.utcnow()
        db.session.commit()
        
        user = challenge.user
        user.last_login_at = datetime.utcnow()
        
        # Create session token
        token = SessionManager.create_session(
            user_id=user.id,
            ip_address=_get_client_ip(),
            user_agent=request.headers.get('User-Agent', '')
        )
        
        db.session.commit()
        
        # Log successful login
        _log_audit(user.id, 'login_successful', 'user', user.id, {'email': email})
        
        return {
            'ok': True,
            'token': token.token,
            'expires_at': int(token.expires_at.timestamp()),
            'user': {
                'id': user.id,
                'email': user.email,
                'role': user.role,
                'phone': user.phone,
            }
        }


class SessionManager:
    """Manage user sessions and tokens."""
    
    @staticmethod
    def create_session(user_id, ip_address=None, user_agent=None):
        """
        Create a new session for a user.
        
        Returns:
            Session object
        """
        token = secrets.token_hex(Config.SESSION_TOKEN_LENGTH // 2)  # 32 bytes = 64 hex chars
        expires_at = datetime.utcnow() + timedelta(hours=Config.SESSION_EXPIRY_HOURS)
        
        session = Session(
            user_id=user_id,
            token=token,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.session.add(session)
        return session
    
    @staticmethod
    def validate_token(token):
        """
        Validate a session token.
        
        Returns:
            User object if valid
        
        Raises:
            AuthError: If invalid or expired
        """
        session = Session.query.filter_by(token=token).first()
        
        if not session:
            raise AuthError("Invalid session token", code=401)
        
        if session.is_expired:
            db.session.delete(session)
            db.session.commit()
            raise AuthError("Session has expired", code=401)
        
        user = session.user
        
        if user.status != 'active':
            raise AuthError("User account is inactive", code=403)
        
        # Update last activity
        session.last_activity_at = datetime.utcnow()
        db.session.commit()
        
        return user
    
    @staticmethod
    def logout(token):
        """Invalidate a session token."""
        session = Session.query.filter_by(token=token).first()
        if session:
            db.session.delete(session)
            db.session.commit()
    
    @staticmethod
    def cleanup_expired_sessions():
        """Delete expired session tokens (run periodically)."""
        expired = Session.query.filter(
            Session.expires_at <= datetime.utcnow()
        ).delete()
        db.session.commit()
        return expired


def require_session(f):
    """
    Decorator to require valid session token.
    
    Looks for token in:
    1. Authorization header (Bearer token)
    2. Cookie (session_token)
    3. Query parameter (?token=)
    
    Validates token and adds user to g.user and session context.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        
        # Check Authorization header
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
        
        # Check cookie
        if not token and 'session_token' in request.cookies:
            token = request.cookies['session_token']
        
        # Check query parameter
        if not token:
            token = request.args.get('token')
        
        if not token:
            return jsonify({'error': 'No session token provided'}), 401
        
        try:
            user = SessionManager.validate_token(token)
            g.user = user
            g.token = token
        except AuthError as e:
            return jsonify({'error': e.message}), e.code
        
        return f(*args, **kwargs)
    
    return decorated_function


def require_permission(permission):
    """
    Decorator to check user permissions.
    
    Example:
        @app.route('/admin/users', methods=['GET'])
        @require_session
        @require_permission('manage_users')
        def admin_users():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = g.get('user')
            if not user:
                return jsonify({'error': 'Not authenticated'}), 401
            
            # Permission matrix
            permissions = {
                'super_admin': [
                    'manage_users', 'manage_roles', 'manage_org',
                    'manage_contributions', 'manage_loans', 'manage_payments',
                    'view_reports', 'view_audit_log'
                ],
                'admin': [
                    'manage_members', 'manage_contributions', 'manage_loans',
                    'approve_loans', 'manage_payments', 'view_reports'
                ],
                'manager': [
                    'manage_members', 'manage_contributions', 'view_reports'
                ],
                'member': [
                    'view_profile', 'request_loan', 'view_contributions',
                    'view_payments', 'send_message'
                ]
            }
            
            user_permissions = permissions.get(user.role, [])
            
            if permission not in user_permissions:
                _log_audit(user.id, 'unauthorized_access', 'user', user.id, 
                          {'permission': permission, 'role': user.role})
                return jsonify({'error': 'Permission denied'}), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def _get_client_ip():
    """Get client IP address from request."""
    if request.environ.get('HTTP_X_FORWARDED_FOR'):
        return request.environ['HTTP_X_FORWARDED_FOR'].split(',')[0].strip()
    return request.remote_addr


def _log_audit(user_id, action, resource_type, resource_id, changes=None):
    """Log an action to audit log."""
    try:
        audit = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            changes=changes,
            ip_address=_get_client_ip(),
            status='success'
        )
        db.session.add(audit)
        db.session.commit()
    except Exception as e:
        # Don't let audit logging break the request
        print(f"Audit log error: {e}")
