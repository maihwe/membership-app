"""
Payment processing and tracking routes.
"""

from flask import Blueprint, request, jsonify, g
from datetime import datetime
from auth import require_session
from models import db, Payment, Contribution, LoanRepayment, Member

bp = Blueprint('payments', __name__, url_prefix='/api/payments')


@bp.route('', methods=['GET'])
@require_session
def list_payments():
    """List payment history."""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    if g.user.role in ['super_admin', 'admin']:
        payments = Payment.query.paginate(page=page, per_page=per_page)
    else:
        member = Member.query.filter_by(user_id=g.user.id).first()
        if not member:
            return jsonify({'error': 'Member profile not found'}), 404
        payments = Payment.query.filter_by(member_id=member.id).paginate(page=page, per_page=per_page)
    
    return jsonify({
        'payments': [{
            'id': p.id,
            'amount': p.amount,
            'type': p.payment_type,
            'method': p.payment_method,
            'created_at': p.created_at.isoformat(),
            'reconciled': p.reconciled_at is not None
        } for p in payments.items],
        'total': payments.total,
        'pages': payments.pages
    }), 200


@bp.route('', methods=['POST'])
@require_session
def record_payment():
    """Record a payment (admin only)."""
    if g.user.role not in ['super_admin', 'admin']:
        return jsonify({'error': 'Permission denied'}), 403
    
    data = request.get_json() or {}
    
    # Validate required fields
    required = ['member_id', 'amount', 'payment_type', 'payment_method']
    if not all(k in data for k in required):
        return jsonify({'error': f'Missing required fields'}), 400
    
    member = Member.query.get(data['member_id'])
    if not member:
        return jsonify({'error': 'Member not found'}), 404
    
    payment = Payment(
        member_id=data['member_id'],
        amount=float(data['amount']),
        payment_type=data['payment_type'],
        payment_method=data['payment_method'],
        reference=data.get('reference'),
        transaction_id=data.get('transaction_id'),
        recorded_by=g.user.id,
        notes=data.get('notes', '')
    )
    db.session.add(payment)
    db.session.commit()
    
    # Auto-reconcile if requested
    if data.get('auto_reconcile'):
        payment.reconciled_at = datetime.utcnow()
        payment.reconciled_by = g.user.id
        
        # Apply payment to contribution or loan
        if data['payment_type'] == 'contribution':
            contribution = Contribution.query.get(data.get('reference'))
            if contribution:
                contribution.amount_paid += payment.amount
                if contribution.amount_paid >= contribution.amount_due:
                    contribution.status = 'paid'
                    contribution.paid_date = datetime.utcnow().date()
                else:
                    contribution.status = 'partial'
        
        elif data['payment_type'] == 'loan_repayment':
            repayment = LoanRepayment.query.get(data.get('reference'))
            if repayment:
                repayment.amount_paid += payment.amount
                if repayment.amount_paid >= repayment.amount_due:
                    repayment.status = 'paid'
                    repayment.paid_date = datetime.utcnow().date()
        
        db.session.commit()
    
    return jsonify({
        'id': payment.id,
        'message': 'Payment recorded'
    }), 201


@bp.route('/<payment_id>/reconcile', methods=['POST'])
@require_session
def reconcile_payment(payment_id):
    """Reconcile a payment (admin only)."""
    if g.user.role not in ['super_admin', 'admin']:
        return jsonify({'error': 'Permission denied'}), 403
    
    payment = Payment.query.get(payment_id)
    if not payment:
        return jsonify({'error': 'Payment not found'}), 404
    
    if payment.reconciled_at:
        return jsonify({'error': 'Payment already reconciled'}), 400
    
    payment.reconciled_at = datetime.utcnow()
    payment.reconciled_by = g.user.id
    db.session.commit()
    
    return jsonify({
        'id': payment.id,
        'message': 'Payment reconciled'
    }), 200


@bp.route('/summary', methods=['GET'])
@require_session
def payment_summary():
    """Get payment summary (admin only)."""
    if g.user.role not in ['super_admin', 'admin']:
        return jsonify({'error': 'Permission denied'}), 403
    
    total_received = db.session.query(db.func.sum(Payment.amount)).scalar() or 0
    total_pending_reconcile = db.session.query(db.func.sum(Payment.amount)).filter(
        Payment.reconciled_at == None
    ).scalar() or 0
    
    return jsonify({
        'total_received': total_received,
        'pending_reconciliation': total_pending_reconcile,
        'reconciled': total_received - total_pending_reconcile,
        'reconciliation_percentage': (
            (total_received - total_pending_reconcile) / total_received * 100
            if total_received > 0 else 0
        )
    }), 200
