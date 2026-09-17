"""
Members management routes.
"""

from flask import Blueprint, request, jsonify, g
from auth import require_session, require_permission
from models import db, User, Member

bp = Blueprint('members', __name__, url_prefix='/api/members')


@bp.route('', methods=['GET'])
@require_session
def list_members():
    """List all members (admin only)."""
    if g.user.role not in ['super_admin', 'admin']:
        return jsonify({'error': 'Permission denied'}), 403
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    members = Member.query.paginate(page=page, per_page=per_page)
    
    return jsonify({
        'members': [{
            'id': m.id,
            'email': m.user.email,
            'phone': m.phone,
            'status': m.status,
            'joined_date': m.joined_date.isoformat(),
        } for m in members.items],
        'total': members.total,
        'pages': members.pages,
        'current_page': page
    }), 200


@bp.route('/<member_id>', methods=['GET'])
@require_session
def get_member(member_id):
    """Get member profile."""
    member = Member.query.get(member_id)
    if not member:
        return jsonify({'error': 'Member not found'}), 404
    
    # Member can view self, admins can view any
    if g.user.id != member.user_id and g.user.role not in ['super_admin', 'admin']:
        return jsonify({'error': 'Permission denied'}), 403
    
    return jsonify({
        'id': member.id,
        'email': member.user.email,
        'phone': member.phone,
        'bio': member.bio,
        'photo_url': member.photo_url,
        'address': member.address,
        'status': member.status,
        'joined_date': member.joined_date.isoformat(),
    }), 200


@bp.route('/<member_id>', methods=['PUT'])
@require_session
def update_member(member_id):
    """Update member profile."""
    member = Member.query.get(member_id)
    if not member:
        return jsonify({'error': 'Member not found'}), 404
    
    # Member can update self, admins can update any
    if g.user.id != member.user_id and g.user.role not in ['super_admin', 'admin']:
        return jsonify({'error': 'Permission denied'}), 403
    
    data = request.get_json() or {}
    
    # Update allowed fields
    if 'phone' in data:
        member.phone = data['phone']
    if 'bio' in data:
        member.bio = data['bio']
    if 'address' in data:
        member.address = data['address']
    if 'photo_url' in data and g.user.role in ['super_admin', 'admin']:
        member.photo_url = data['photo_url']
    
    db.session.commit()
    
    return jsonify({
        'id': member.id,
        'phone': member.phone,
        'bio': member.bio,
        'address': member.address,
        'message': 'Member updated'
    }), 200


@bp.route('', methods=['POST'])
@require_session
def create_member():
    """Create new member (admin only)."""
    if g.user.role not in ['super_admin', 'admin']:
        return jsonify({'error': 'Permission denied'}), 403
    
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    phone = data.get('phone', '')
    
    if not email:
        return jsonify({'error': 'Email is required'}), 400
    
    # Create user
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(email=email, role='member', phone=phone)
        db.session.add(user)
        db.session.commit()
    
    # Create member profile
    member = Member.query.filter_by(user_id=user.id).first()
    if member:
        return jsonify({'error': 'Member already exists'}), 409
    
    member = Member(
        user_id=user.id,
        org_id='default',
        phone=phone,
        bio=data.get('bio', '')
    )
    db.session.add(member)
    db.session.commit()
    
    return jsonify({
        'id': member.id,
        'email': user.email,
        'message': 'Member created'
    }), 201
