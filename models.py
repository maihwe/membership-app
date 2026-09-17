"""
SQLAlchemy models for the membership management system.

Entities:
- User: Authentication identity (email + session)
- Member: Organization member (profile, contributions, loans)
- Contribution: Member's financial obligation to organization
- ContributionCycle: Period/scheme for contributions (fixed or rotating)
- Loan: Member loan request and tracking
- LoanRepayment: Repayment schedule for loans
- Payment: Payment record (received from member)
- Message: Internal messaging between members/admins
- Session: Active user sessions (tokens)
- AuditLog: Activity log for compliance/debugging
"""

from datetime import datetime, timedelta
import uuid
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

db = SQLAlchemy()


class User(db.Model):
    """Authentication user - represents a loginable account."""
    __tablename__ = 'users'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20))
    role = db.Column(db.String(50), nullable=False, default='member')  # super_admin, admin, manager, member
    status = db.Column(db.String(20), nullable=False, default='active')  # active, inactive, suspended
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = db.Column(db.DateTime)
    
    # Relationships
    member = db.relationship('Member', uselist=False, back_populates='user')
    sessions = db.relationship('Session', back_populates='user', cascade='all, delete-orphan')
    otp_challenges = db.relationship('OTPChallenge', back_populates='user', cascade='all, delete-orphan')
    messages_sent = db.relationship('Message', foreign_keys='Message.sender_id', back_populates='sender')
    audit_logs = db.relationship('AuditLog', back_populates='user')
    
    def __repr__(self):
        return f'<User {self.email}>'


class Member(db.Model):
    """Organization member - profile and participation tracking."""
    __tablename__ = 'members'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, unique=True)
    org_id = db.Column(db.String(36), nullable=False)  # Organization ID (single for MVP)
    status = db.Column(db.String(20), nullable=False, default='active')  # active, inactive, suspended
    bio = db.Column(db.Text)
    photo_url = db.Column(db.String(255))
    phone = db.Column(db.String(20))
    address = db.Column(db.String(255))
    date_of_birth = db.Column(db.Date)
    joined_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='member')
    contributions = db.relationship('Contribution', back_populates='member', cascade='all, delete-orphan')
    loans = db.relationship('Loan', back_populates='member', cascade='all, delete-orphan')
    payments = db.relationship('Payment', back_populates='member')
    
    def __repr__(self):
        return f'<Member {self.user.email}>'


class ContributionCycle(db.Model):
    """A contribution period/scheme (fixed amount vs rotating pool)."""
    __tablename__ = 'contribution_cycles'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = db.Column(db.String(36), nullable=False)
    name = db.Column(db.String(120), nullable=False)  # e.g., "August 2024 Fixed Contribution"
    scheme_type = db.Column(db.String(20), nullable=False)  # 'fixed' or 'rotating'
    amount = db.Column(db.Float, nullable=False)  # For fixed: fixed amount; for rotating: pool amount
    currency = db.Column(db.String(3), nullable=False, default='NGN')
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='active')  # active, closed, archived
    member_count = db.Column(db.Integer, default=0)  # For rotating pool: who gets paid this cycle
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    contributions = db.relationship('Contribution', back_populates='cycle')
    
    def __repr__(self):
        return f'<ContributionCycle {self.name}>'


class Contribution(db.Model):
    """A member's financial obligation for a contribution cycle."""
    __tablename__ = 'contributions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    member_id = db.Column(db.String(36), db.ForeignKey('members.id'), nullable=False)
    cycle_id = db.Column(db.String(36), db.ForeignKey('contribution_cycles.id'), nullable=False)
    amount_due = db.Column(db.Float, nullable=False)
    amount_paid = db.Column(db.Float, nullable=False, default=0.0)
    penalty_amount = db.Column(db.Float, nullable=False, default=0.0)
    due_date = db.Column(db.Date, nullable=False)
    paid_date = db.Column(db.Date)
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, partial, paid, overdue, default
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    member = db.relationship('Member', back_populates='contributions')
    cycle = db.relationship('ContributionCycle', back_populates='contributions')
    
    @property
    def is_overdue(self):
        if self.status in ['paid', 'default']:
            return False
        return datetime.utcnow().date() > self.due_date
    
    def __repr__(self):
        return f'<Contribution {self.member.user.email} - {self.cycle.name}>'


class Loan(db.Model):
    """A member loan request and tracking."""
    __tablename__ = 'loans'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    member_id = db.Column(db.String(36), db.ForeignKey('members.id'), nullable=False)
    amount_requested = db.Column(db.Float, nullable=False)
    amount_approved = db.Column(db.Float)
    interest_rate = db.Column(db.Float, default=0.0)
    repayment_months = db.Column(db.Integer, default=12)
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, approved, rejected, disbursed, repaid, defaulted
    purpose = db.Column(db.Text)
    requested_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    approved_by = db.Column(db.String(36), db.ForeignKey('users.id'))
    approved_at = db.Column(db.DateTime)
    disbursed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    member = db.relationship('Member', back_populates='loans')
    approver = db.relationship('User', foreign_keys=[approved_by])
    repayments = db.relationship('LoanRepayment', back_populates='loan', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Loan {self.member.user.email} - {self.amount_requested}>'


class LoanRepayment(db.Model):
    """Repayment schedule/tracking for a loan."""
    __tablename__ = 'loan_repayments'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    loan_id = db.Column(db.String(36), db.ForeignKey('loans.id'), nullable=False)
    installment_number = db.Column(db.Integer, nullable=False)
    amount_due = db.Column(db.Float, nullable=False)
    amount_paid = db.Column(db.Float, default=0.0)
    due_date = db.Column(db.Date, nullable=False)
    paid_date = db.Column(db.Date)
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, paid, overdue, defaulted
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    loan = db.relationship('Loan', back_populates='repayments')
    
    def __repr__(self):
        return f'<LoanRepayment Loan {self.loan_id} - Installment {self.installment_number}>'


class Payment(db.Model):
    """A payment received from a member (contribution, loan repayment, etc.)."""
    __tablename__ = 'payments'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    member_id = db.Column(db.String(36), db.ForeignKey('members.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_type = db.Column(db.String(50), nullable=False)  # 'contribution', 'loan_repayment', 'penalty', 'other'
    reference = db.Column(db.String(120))  # Reference ID (contribution_id, loan_repayment_id, etc.)
    payment_method = db.Column(db.String(50))  # 'cash', 'bank_transfer', 'mobile_money', 'check'
    transaction_id = db.Column(db.String(120))  # Bank/payment provider reference
    recorded_by = db.Column(db.String(36), db.ForeignKey('users.id'))  # Who recorded this payment
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    reconciled_at = db.Column(db.DateTime)
    reconciled_by = db.Column(db.String(36), db.ForeignKey('users.id'))
    
    # Relationships
    member = db.relationship('Member', back_populates='payments')
    recorder = db.relationship('User', foreign_keys=[recorded_by])
    reconciler = db.relationship('User', foreign_keys=[reconciled_by])
    
    def __repr__(self):
        return f'<Payment {self.member.user.email} - {self.amount}>'


class Message(db.Model):
    """Internal messaging between members and admins."""
    __tablename__ = 'messages'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sender_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    recipient_email = db.Column(db.String(120), nullable=False)  # Who the message is for
    subject = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(50), default='message')  # 'message', 'notification', 'alert'
    status = db.Column(db.String(20), default='unread')  # unread, read, archived
    attachment_url = db.Column(db.String(255))  # File attachment if any
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    read_at = db.Column(db.DateTime)
    
    # Relationships
    sender = db.relationship('User', back_populates='messages_sent', foreign_keys=[sender_id])
    
    def __repr__(self):
        return f'<Message {self.subject}>'


class OTPChallenge(db.Model):
    """OTP challenge for passwordless authentication."""
    __tablename__ = 'otp_challenges'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    email = db.Column(db.String(120), nullable=False, index=True)
    code_hash = db.Column(db.String(255), nullable=False)  # Hashed OTP
    attempts = db.Column(db.Integer, default=0)  # Failed attempts
    status = db.Column(db.String(20), default='pending')  # pending, verified, expired, failed
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    verified_at = db.Column(db.DateTime)
    
    # Relationships
    user = db.relationship('User', back_populates='otp_challenges')
    
    @property
    def is_expired(self):
        return datetime.utcnow() > self.expires_at
    
    def __repr__(self):
        return f'<OTPChallenge {self.email}>'


class Session(db.Model):
    """User session - tracks active login tokens."""
    __tablename__ = 'sessions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)  # 32-byte random token
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_activity_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    ip_address = db.Column(db.String(45))  # IPv4 or IPv6
    user_agent = db.Column(db.String(255))  # Browser/app info
    
    # Relationships
    user = db.relationship('User', back_populates='sessions')
    
    @property
    def is_expired(self):
        return datetime.utcnow() > self.expires_at
    
    def __repr__(self):
        return f'<Session {self.user.email}>'


class AuditLog(db.Model):
    """Audit log for compliance and debugging."""
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'))
    action = db.Column(db.String(100), nullable=False)  # 'login', 'create_member', 'approve_loan', etc.
    resource_type = db.Column(db.String(50))  # 'user', 'member', 'loan', 'payment', etc.
    resource_id = db.Column(db.String(36))  # ID of the resource affected
    changes = db.Column(db.JSON)  # What changed (before/after)
    ip_address = db.Column(db.String(45))
    status = db.Column(db.String(20), default='success')  # success, failed, error
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Relationships
    user = db.relationship('User', back_populates='audit_logs')
    
    def __repr__(self):
        return f'<AuditLog {self.action} - {self.resource_type}>'


# Indexes for common queries
db.Index('idx_user_email', User.email)
db.Index('idx_member_user_id', Member.user_id)
db.Index('idx_contribution_member_cycle', Contribution.member_id, Contribution.cycle_id)
db.Index('idx_loan_member', Loan.member_id)
db.Index('idx_payment_member', Payment.member_id)
db.Index('idx_session_user', Session.user_id)
db.Index('idx_session_token', Session.token)
db.Index('idx_otp_email', OTPChallenge.email)
db.Index('idx_audit_created', AuditLog.created_at)
