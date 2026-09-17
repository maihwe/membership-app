"""
Contributions management routes.
"""

from flask import Blueprint, request, jsonify, g
from datetime import datetime
from auth import require_session
from models import db, Contribution, ContributionCycle, Member

bp = Blueprint('contributions', __name__, url_prefix='/api/contributions')


@bp.route('', methods=['GET'])
@require_session
def list_contributions():
    """List contributions for current user or all (admin)."""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    if g.user.role in ['super_admin', 'admin']:
        # Admin sees all
        contributions = Contribution.query.paginate(page=page, per_page=per_page)
    else:
        # Member sees only their own
        member = Member.query.filter_by(user_id=g.user.id).first()
        if not member:
            return jsonify({'error': 'Member profile not found'}), 404
        contributions = Contribution.query.filter_by(member_id=member.id).paginate(page=page, per_page=per_page)
    
    return jsonify({
        'contributions': [{
            'id': c.id,
            'cycle': c.cycle.name,
            'amount_due': c.amount_due,
            'amount_paid': c.amount_paid,
            'status': c.status,
            'due_date': c.due_date.isoformat(),
            'is_overdue': c.is_overdue
        } for c in contributions.items],
        'total': contributions.total,
        'pages': contributions.pages
    }), 200


@bp.route('/<contribution_id>', methods=['GET'])
@require_session
def get_contribution(contribution_id):
    """Get contribution details."""
    contribution = Contribution.query.get(contribution_id)
    if not contribution:
        return jsonify({'error': 'Contribution not found'}), 404
    
    # User can view their own, admins can view any
    if g.user.id != contribution.member.user_id and g.user.role not in ['super_admin', 'admin']:
        return jsonify({'error': 'Permission denied'}), 403
    
    return jsonify({
        'id': contribution.id,
        'cycle': contribution.cycle.name,
        'member_email': contribution.member.user.email,
        'amount_due': contribution.amount_due,
        'amount_paid': contribution.amount_paid,
        'penalty_amount': contribution.penalty_amount,
        'status': contribution.status,
        'due_date': contribution.due_date.isoformat(),
        'paid_date': contribution.paid_date.isoformat() if contribution.paid_date else None,
        'is_overdue': contribution.is_overdue,
        'notes': contribution.notes
    }), 200


@bp.route('/cycles', methods=['GET'])
@require_session
def list_cycles():
    """List contribution cycles (admin only)."""
    if g.user.role not in ['super_admin', 'admin']:
        return jsonify({'error': 'Permission denied'}), 403
    
    cycles = ContributionCycle.query.all()
    
    return jsonify({
        'cycles': [{
            'id': c.id,
            'name': c.name,
            'type': c.scheme_type,
            'amount': c.amount,
            'start_date': c.start_date.isoformat(),
            'end_date': c.end_date.isoformat(),
            'due_date': c.due_date.isoformat(),
            'status': c.status,
            'member_count': c.member_count
        } for c in cycles]
    }), 200


@bp.route('/cycles', methods=['POST'])
@require_session
def create_cycle():
    """Create new contribution cycle (admin only)."""
    if g.user.role not in ['super_admin', 'admin']:
        return jsonify({'error': 'Permission denied'}), 403
    
    data = request.get_json() or {}
    
    # Validate required fields
    required = ['name', 'scheme_type', 'amount', 'start_date', 'end_date', 'due_date']
    if not all(k in data for k in required):
        return jsonify({'error': f'Missing required fields: {", ".join(required)}'}), 400
    
    # Parse dates
    try:
        start_date = datetime.fromisoformat(data['start_date']).date()
        end_date = datetime.fromisoformat(data['end_date']).date()
        due_date = datetime.fromisoformat(data['due_date']).date()
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400
    
    cycle = ContributionCycle(
        org_id='default',
        name=data['name'],
        scheme_type=data['scheme_type'],
        amount=float(data['amount']),
        currency=data.get('currency', 'NGN'),
        start_date=start_date,
        end_date=end_date,
        due_date=due_date,
        member_count=data.get('member_count', 0)
    )
    db.session.add(cycle)
    db.session.commit()
    
    return jsonify({
        'id': cycle.id,
        'message': 'Cycle created'
    }), 201
