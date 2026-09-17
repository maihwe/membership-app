"""
Internal messaging routes.
"""

from flask import Blueprint, request, jsonify, g
from datetime import datetime
from auth import require_session
from models import db, Message, User

bp = Blueprint('messages', __name__, url_prefix='/api/messages')


@bp.route('', methods=['GET'])
@require_session
def inbox():
    """Get user's inbox."""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', None)  # 'unread', 'read', etc.
    
    query = Message.query.filter_by(recipient_email=g.user.email)
    
    if status:
        query = query.filter_by(status=status)
    
    messages = query.order_by(Message.created_at.desc()).paginate(page=page, per_page=20)
    
    return jsonify({
        'messages': [{
            'id': m.id,
            'from': m.sender.email,
            'subject': m.subject,
            'body': m.body[:200],  # Preview
            'type': m.message_type,
            'status': m.status,
            'created_at': m.created_at.isoformat(),
            'read_at': m.read_at.isoformat() if m.read_at else None,
        } for m in messages.items],
        'total': messages.total,
        'pages': messages.pages,
        'unread_count': Message.query.filter_by(
            recipient_email=g.user.email,
            status='unread'
        ).count()
    }), 200


@bp.route('/<message_id>', methods=['GET'])
@require_session
def get_message(message_id):
    """Get message details."""
    message = Message.query.get(message_id)
    if not message:
        return jsonify({'error': 'Message not found'}), 404
    
    if message.recipient_email != g.user.email and message.sender_id != g.user.id:
        return jsonify({'error': 'Permission denied'}), 403
    
    # Mark as read
    if message.recipient_email == g.user.email and message.status == 'unread':
        message.status = 'read'
        message.read_at = datetime.utcnow()
        db.session.commit()
    
    return jsonify({
        'id': message.id,
        'from': message.sender.email,
        'to': message.recipient_email,
        'subject': message.subject,
        'body': message.body,
        'type': message.message_type,
        'status': message.status,
        'attachment_url': message.attachment_url,
        'created_at': message.created_at.isoformat(),
        'read_at': message.read_at.isoformat() if message.read_at else None,
    }), 200


@bp.route('', methods=['POST'])
@require_session
def send_message():
    """Send a message to another member."""
    data = request.get_json() or {}
    
    recipient_email = data.get('recipient_email', '').strip().lower()
    subject = data.get('subject', '').strip()
    body = data.get('body', '').strip()
    
    if not all([recipient_email, subject, body]):
        return jsonify({'error': 'Recipient, subject, and body are required'}), 400
    
    recipient = User.query.filter_by(email=recipient_email).first()
    if not recipient:
        return jsonify({'error': 'Recipient not found'}), 404
    
    message = Message(
        sender_id=g.user.id,
        recipient_email=recipient_email,
        subject=subject,
        body=body,
        message_type='message',
        status='unread',
        attachment_url=data.get('attachment_url')
    )
    db.session.add(message)
    db.session.commit()
    
    return jsonify({
        'id': message.id,
        'message': 'Message sent'
    }), 201


@bp.route('/<message_id>/mark-read', methods=['POST'])
@require_session
def mark_read(message_id):
    """Mark message as read."""
    message = Message.query.get(message_id)
    if not message:
        return jsonify({'error': 'Message not found'}), 404
    
    if message.recipient_email != g.user.email:
        return jsonify({'error': 'Permission denied'}), 403
    
    message.status = 'read'
    message.read_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({'message': 'Marked as read'}), 200


@bp.route('/<message_id>/archive', methods=['POST'])
@require_session
def archive_message(message_id):
    """Archive a message."""
    message = Message.query.get(message_id)
    if not message:
        return jsonify({'error': 'Message not found'}), 404
    
    if message.recipient_email != g.user.email and message.sender_id != g.user.id:
        return jsonify({'error': 'Permission denied'}), 403
    
    message.status = 'archived'
    db.session.commit()
    
    return jsonify({'message': 'Archived'}), 200
