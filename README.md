# Membership Management System

A passwordless, role-based membership management platform for organizations (savings groups, mutual aid societies, rotating credit associations).

**Built in:** Python + Flask + SQLite + Email  
**Deployment:** Self-hosted (Linux/Docker)  
**Architecture:** Clean separation of auth, permissions, state management

---

## Features

- **Passwordless OTP Authentication** (email-based login)
- **Role-Based Access Control** (Super Admin, Admin, Manager, Member)
- **User Management** (profiles, roles, activity logging)
- **Contribution Schemes** (fixed-amount and rotating pools with penalties)
- **Loan Management** (requests, approvals, repayment schedules)
- **Payment Tracking** (ledger, reconciliation, late-payment penalties)
- **Internal Messaging** (member-to-member + admin notifications)
- **Financial Dashboards** (member view + admin view)
- **Email Notifications** (OTP, payment reminders, loan updates)

---

## Quick Start

### 1. Prerequisites
- Python 3.9+
- SQLite3
- Email account (SMTP)

### 2. Setup

```bash
# Clone/extract the project
cd membership-app

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your email credentials and org details

# Initialize database
python init_db.py

# Run the app
flask run
```

The app will be available at `http://localhost:5000`

---

## Project Structure

```
membership-app/
├── app/
│   ├── __init__.py              # Flask app factory
│   ├── models.py                # SQLAlchemy models (User, Member, Contribution, etc.)
│   ├── auth.py                  # OTP generation, verification, session management
│   ├── permissions.py           # Role-based access control
│   ├── email_service.py         # Email sending
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py              # Login, logout, OTP verification
│   │   ├── members.py           # Member management
│   │   ├── contributions.py     # Contribution tracking
│   │   ├── loans.py             # Loan management
│   │   ├── payments.py          # Payment processing
│   │   ├── messages.py          # Messaging
│   │   └── admin.py             # Admin dashboards
│   ├── templates/
│   │   ├── base.html            # Base layout
│   │   ├── auth/
│   │   │   ├── login.html
│   │   │   └── verify.html
│   │   ├── members/
│   │   ├── contributions/
│   │   ├── loans/
│   │   ├── messages/
│   │   └── admin/
│   └── static/
│       ├── css/
│       └── js/
├── migrations/                  # Database migrations (Alembic)
├── config.py                    # Configuration management
├── init_db.py                   # Database initialization
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variables template
├── docker-compose.yml           # Docker deployment
└── Dockerfile                   # Docker image definition
```

---

## Architecture

### Authentication Flow
1. User requests login → system generates 6-digit OTP
2. OTP hashed and stored with 10-minute expiry
3. User receives OTP via email
4. User submits OTP → system verifies using constant-time comparison
5. Successful verification → session token issued (12-hour expiry)
6. All subsequent requests validated against session token

### Permission Model
- Every route requires `@require_session` decorator
- Session contains user, role, permissions
- Each operation checked against user's role permissions
- Fail-fast on unauthorized access

### State Management
- SQLite for persistent storage
- In-memory caching for sessions (can swap to Redis)
- Transaction support for financial operations
- Audit logging for all state changes

---

## Environment Configuration

See `.env.example` for all settings:

```
FLASK_ENV=production
SECRET_KEY=<random-32-char-key>
DATABASE_URL=sqlite:///membership.db
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
ORG_NAME=Your Organization
ORG_EMAIL=noreply@yourorg.com
```

---

## Deployment

### Local (Development)
```bash
flask run
```

### Docker (Production)
```bash
docker-compose up -d
```

The app runs on port 5000. Configure reverse proxy (nginx/Apache) for production.

---

## Database Schema

**Users:** email, password_hash, role, status, created_at  
**Members:** user_id, org_id, status, phone, photo_url, bio  
**Contributions:** member_id, cycle_id, scheme_id, amount, due_date, paid_date, status  
**Loans:** member_id, amount, approved_by, approval_date, repayment_schedule, status  
**Payments:** member_id, amount, type, reference, created_at, reconciled_by  
**Messages:** sender_id, recipient_id, subject, body, attachments, created_at  
**Sessions:** token, user_id, expires_at, created_at  
**AuditLog:** user_id, action, resource, changes, created_at

---

## Security Notes

- **Never store plaintext passwords.** All auth is passwordless OTP.
- **OTPs hashed with bcrypt** before storage.
- **Session tokens are 32-byte random strings** (cryptographically secure).
- **Constant-time comparison** prevents timing attacks on OTP verification.
- **SQL injection prevented** via SQLAlchemy ORM (parameterized queries).
- **CSRF protection** on all forms (Flask-WTF).
- **Rate limiting** on OTP requests (max 5 per hour per email).
- **Activity logging** for audit trail.

---

## API Endpoints (Summary)

**Auth:**
- `POST /auth/request-code` → Request OTP
- `POST /auth/verify` → Verify OTP + get session token
- `POST /auth/logout` → Invalidate session

**Members:**
- `GET /members` → List members (admin)
- `GET /members/<id>` → Member profile
- `POST /members` → Create member (admin)
- `PUT /members/<id>` → Update profile

**Contributions:**
- `GET /contributions` → List contributions
- `POST /contributions/<id>/pay` → Record payment

**Loans:**
- `POST /loans/request` → Request loan
- `GET /loans` → List loans
- `POST /loans/<id>/approve` → Approve loan (admin)
- `POST /loans/<id>/repay` → Record repayment

**Payments:**
- `GET /payments` → Payment history
- `POST /payments` → Record payment

**Messages:**
- `GET /messages` → Inbox
- `POST /messages/send` → Send message

**Admin:**
- `GET /admin/dashboard` → Organization overview
- `GET /admin/members` → Member management
- `GET /admin/contributions` → Contribution tracking
- `GET /admin/payments` → Payment reconciliation
- `GET /admin/audit-log` → Activity log

---

## Development Notes

**Testing:**
```bash
pytest tests/
```

**Database migrations:**
```bash
flask db migrate -m "description"
flask db upgrade
```

**Email testing** (development):
Set `MAIL_BACKEND=console` in `.env` to print emails to stdout.

---

## Support

For issues or questions, refer to the code comments or the architecture diagram in `/docs/architecture.md`.

---

**Version:** 1.0.0  
**Last Updated:** September 2026
#
