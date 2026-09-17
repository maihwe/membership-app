"""
Admin dashboard and management routes.
"""

from flask import Blueprint, request, jsonify, g
from datetime import datetime, timedelta
from sqlalchemy import func
from auth import require_session
from models import (
    db, User, Member, Contribution, Loan, Payment, 
    AuditLog, ContributionCycle
)

bp = Blueprint('admin', __name__, url_prefix='/api/admin')


def require_admin(f):
    """Decorator to require admin role."""
    def wrapper(*args, **kwargs):
        if g.user.role not in ['super_admin', 'admin']:
            return jsonify({'error': 'Permission denied'}), 403
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper


@bp.route('/dashboard', methods=['GET'])
@require_session
@require_admin
def dashboard():
    """Organization overview dashboard."""
    
    # Member statistics
    total_members = Member.query.count()
    active_members = Member.query.filter_by(status='active').count()
    
    # Contribution statistics
    total_due = db.session.query(func.sum(Contribution.amount_due)).scalar() or 0
    total_paid = db.session.query(func.sum(Contribution.amount_paid)).scalar() or 0
    
    # Loan statistics
    total_loans_requested = db.session.query(func.sum(Loan.amount_requested)).filter(
        Loan.status != 'rejected'
    ).scalar() or 0
    total_loans_approved = db.session.query(func.sum(Loan.amount_approved)).filter(
        Loan.status.in_(['approved', 'disbursed'])
    ).scalar() or 0
    
    # Payment statistics
    total_payments_received = db.session.query(func.sum(Payment.amount)).scalar() or 0
    
    # Overdue contributions
    overdue_count = Contribution.query.filter(
        Contribution.status.in_(['pending', 'partial']),
        Contribution.due_date < datetime.utcnow().date()
    ).count()
    
    return jsonify({
        'members': {
            'total': total_members,
            'active': active_members,
            'inactive': total_members - active_members
        },
        'contributions': {
            'total_due': total_due,
            'total_paid': total_paid,
            'collection_rate': (total_paid / total_due * 100) if total_due > 0 else 0,
            'overdue_count': overdue_count
        },
        'loans': {
            'total_requested': total_loans_requested,
            'total_approved': total_loans_approved,
            'approval_rate': (total_loans_approved / total_loans_requested * 100) if total_loans_requested > 0 else 0
        },
        'payments': {
            'total_received': total_payments_received
        }
    }), 200


@bp.route('/members', methods=['GET'])
@require_session
@require_admin
def admin_members():
    """Member management (admin)."""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status')  # Filter by status
    
    query = Member.query
    if status:
        query = query.filter_by(status=status)
    
    members = query.paginate(page=page, per_page=20)
    
    return jsonify({
        'members': [{
            'id': m.id,
            'email': m.user.email,
            'phone': m.phone,
            'status': m.status,
            'joined_date': m.joined_date.isoformat(),
            'total_contributed': sum(c.amount_paid for c in m.contributions),
            'total_loans': sum(l.amount_requested for l in m.loans)
        } for m in members.items],
        'total': members.total,
        'pages': members.pages
    }), 200


@bp.route('/members/<member_id>/suspend', methods=['POST'])
@require_session
@require_admin
def suspend_member(member_id):
    """Suspend a member account."""
    member = Member.query.get(member_id)
    if not member:
        return jsonify({'error': 'Member not found'}), 404
    
    member.status = 'suspended'
    member.user.status = 'suspended'
    db.session.commit()
    
    return jsonify({'message': 'Member suspended'}), 200


@bp.route('/contributions/cycles', methods=['GET'])
@require_session
@require_admin
def view_cycles():
    """View all contribution cycles."""
    cycles = ContributionCycle.query.all()
    
    return jsonify({
        'cycles': [{
            'id': c.id,
            'name': c.name,
            'type': c.scheme_type,
            'amount': c.amount,
            'status': c.status,
            'start_date': c.start_date.isoformat(),
            'end_date': c.end_date.isoformat(),
            'due_date': c.due_date.isoformat(),
            'contributions': len(c.contributions),
            'amount_collected': sum(co.amount_paid for co in c.contributions),
            'amount_due': sum(co.amount_due for co in c.contributions)
        } for c in cycles]
    }), 200


@bp.route('/loans/pending', methods=['GET'])
@require_session
@require_admin
def pending_loans():
    """Get pending loan requests for approval."""
    page = request.args.get('page', 1, type=int)
    
    loans = Loan.query.filter_by(status='pending').paginate(page=page, per_page=20)
    
    return jsonify({
        'loans': [{
            'id': l.id,
            'member_email': l.member.user.email,
            'amount_requested': l.amount_requested,
            'purpose': l.purpose,
            'requested_at': l.requested_at.isoformat()
        } for l in loans.items],
        'total': loans.total,
        'pages': loans.pages
    }), 200


@bp.route('/payments/reconcile', methods=['GET'])
@require_session
@require_admin
def payments_to_reconcile():
    """Get payments pending reconciliation."""
    page = request.args.get('page', 1, type=int)
    
    payments = Payment.query.filter(
        Payment.reconciled_at == None
    ).paginate(page=page, per_page=20)
    
    total_unreconciled = db.session.query(func.sum(Payment.amount)).filter(
        Payment.reconciled_at == None
    ).scalar() or 0
    
    return jsonify({
        'payments': [{
            'id': p.id,
            'member_email': p.member.user.email,
            'amount': p.amount,
            'type': p.payment_type,
            'method': p.payment_method,
            'recorded_at': p.created_at.isoformat()
        } for p in payments.items],
        'total_pending': total_unreconciled,
        'page_total': payments.total,
        'pages': payments.pages
    }), 200


@bp.route('/audit-log', methods=['GET'])
@require_session
@require_admin
def audit_log():
    """View activity audit log."""
    page = request.args.get('page', 1, type=int)
    action = request.args.get('action')  # Filter by action
    days = request.args.get('days', 7, type=int)  # Last N days
    
    since = datetime.utcnow() - timedelta(days=days)
    query = AuditLog.query.filter(AuditLog.created_at >= since)
    
    if action:
        query = query.filter_by(action=action)
    
    logs = query.order_by(AuditLog.created_at.desc()).paginate(page=page, per_page=50)
    
    return jsonify({
        'logs': [{
            'id': l.id,
            'user': l.user.email if l.user else 'System',
            'action': l.action,
            'resource': l.resource_type,
            'status': l.status,
            'created_at': l.created_at.isoformat()
        } for l in logs.items],
        'total': logs.total,
        'pages': logs.pages
    }), 200


@bp.route('/roles/<user_id>/change', methods=['POST'])
@require_session
def change_user_role(user_id):
    """Change user role (super_admin only)."""
    if g.user.role != 'super_admin':
        return jsonify({'error': 'Only super admins can change roles'}), 403
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json() or {}
    new_role = data.get('role')
    
    if new_role not in ['super_admin', 'admin', 'manager', 'member']:
        return jsonify({'error': 'Invalid role'}), 400
    
    user.role = new_role
    db.session.commit()
    
    return jsonify({
        'id': user.id,
        'email': user.email,
        'role': user.role,
        'message': 'Role updated'
    }), 200


@bp.route('/system/stats', methods=['GET'])
@require_session
@require_admin
def system_stats():
    """System-wide statistics."""
    return jsonify({
        'users': {
            'total': User.query.count(),
            'active': User.query.filter_by(status='active').count(),
            'by_role': {
                'super_admin': User.query.filter_by(role='super_admin').count(),
                'admin': User.query.filter_by(role='admin').count(),
                'manager': User.query.filter_by(role='manager').count(),
                'member': User.query.filter_by(role='member').count(),
            }
        },
        'members': {
            'total': Member.query.count()
        },
        'financials': {
            'total_contributed': db.session.query(func.sum(Contribution.amount_paid)).scalar() or 0,
            'total_loaned': db.session.query(func.sum(Loan.amount_approved)).scalar() or 0,
            'total_received': db.session.query(func.sum(Payment.amount)).scalar() or 0
        }
    }), 200
