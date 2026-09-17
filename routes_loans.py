"""
Loan management routes.
"""

from flask import Blueprint, request, jsonify, g
from datetime import datetime, timedelta
from auth import require_session
from models import db, Loan, LoanRepayment, Member

bp = Blueprint('loans', __name__, url_prefix='/api/loans')


@bp.route('', methods=['GET'])
@require_session
def list_loans():
    """List loans for current user or all (admin)."""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    if g.user.role in ['super_admin', 'admin']:
        loans = Loan.query.paginate(page=page, per_page=per_page)
    else:
        member = Member.query.filter_by(user_id=g.user.id).first()
        if not member:
            return jsonify({'error': 'Member profile not found'}), 404
        loans = Loan.query.filter_by(member_id=member.id).paginate(page=page, per_page=per_page)
    
    return jsonify({
        'loans': [{
            'id': l.id,
            'amount_requested': l.amount_requested,
            'amount_approved': l.amount_approved,
            'status': l.status,
            'requested_at': l.requested_at.isoformat(),
        } for l in loans.items],
        'total': loans.total,
        'pages': loans.pages
    }), 200


@bp.route('', methods=['POST'])
@require_session
def request_loan():
    """Request a new loan."""
    member = Member.query.filter_by(user_id=g.user.id).first()
    if not member:
        return jsonify({'error': 'Member profile not found'}), 404
    
    data = request.get_json() or {}
    
    if not data.get('amount_requested'):
        return jsonify({'error': 'Amount is required'}), 400
    
    loan = Loan(
        member_id=member.id,
        amount_requested=float(data['amount_requested']),
        purpose=data.get('purpose', ''),
        repayment_months=data.get('repayment_months', 12),
        interest_rate=data.get('interest_rate', 0.0)
    )
    db.session.add(loan)
    db.session.commit()
    
    return jsonify({
        'id': loan.id,
        'message': 'Loan request submitted'
    }), 201


@bp.route('/<loan_id>', methods=['GET'])
@require_session
def get_loan(loan_id):
    """Get loan details."""
    loan = Loan.query.get(loan_id)
    if not loan:
        return jsonify({'error': 'Loan not found'}), 404
    
    if g.user.id != loan.member.user_id and g.user.role not in ['super_admin', 'admin']:
        return jsonify({'error': 'Permission denied'}), 403
    
    return jsonify({
        'id': loan.id,
        'amount_requested': loan.amount_requested,
        'amount_approved': loan.amount_approved,
        'status': loan.status,
        'purpose': loan.purpose,
        'repayment_months': loan.repayment_months,
        'interest_rate': loan.interest_rate,
        'requested_at': loan.requested_at.isoformat(),
        'approved_at': loan.approved_at.isoformat() if loan.approved_at else None,
        'repayments': [{
            'id': r.id,
            'installment': r.installment_number,
            'amount_due': r.amount_due,
            'amount_paid': r.amount_paid,
            'due_date': r.due_date.isoformat(),
            'status': r.status
        } for r in loan.repayments]
    }), 200


@bp.route('/<loan_id>/approve', methods=['POST'])
@require_session
def approve_loan(loan_id):
    """Approve a loan request (admin only)."""
    if g.user.role not in ['super_admin', 'admin']:
        return jsonify({'error': 'Permission denied'}), 403
    
    loan = Loan.query.get(loan_id)
    if not loan:
        return jsonify({'error': 'Loan not found'}), 404
    
    if loan.status != 'pending':
        return jsonify({'error': 'Only pending loans can be approved'}), 400
    
    data = request.get_json() or {}
    amount_approved = data.get('amount_approved', loan.amount_requested)
    
    loan.amount_approved = float(amount_approved)
    loan.status = 'approved'
    loan.approved_by = g.user.id
    loan.approved_at = datetime.utcnow()
    
    # Create repayment schedule
    monthly_amount = loan.amount_approved / loan.repayment_months
    for i in range(loan.repayment_months):
        repayment = LoanRepayment(
            loan_id=loan.id,
            installment_number=i + 1,
            amount_due=monthly_amount,
            due_date=(datetime.utcnow() + timedelta(days=30*(i+1))).date()
        )
        db.session.add(repayment)
    
    db.session.commit()
    
    return jsonify({
        'id': loan.id,
        'status': 'approved',
        'message': 'Loan approved'
    }), 200
