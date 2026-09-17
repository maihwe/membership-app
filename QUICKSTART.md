# Membership App - Quick Start Guide

**Deadline: September 21, 2026**  
**Current Status: Core system ready for deployment**

---

## Installation & Setup (5 minutes)

### Prerequisites
- Python 3.9+
- Git
- Email account (Gmail recommended)

### Step 1: Clone/Extract Project

```bash
cd membership-app
```

### Step 2: Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and fill in:

```env
SECRET_KEY=generate-a-random-32-char-string-here
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-specific-password
ORG_NAME=Your Organization Name
ORG_EMAIL=noreply@yourorg.com
```

**For Gmail:**
1. Enable 2-factor authentication
2. Go to https://myaccount.google.com/apppasswords
3. Generate an "App Password" for Mail
4. Use that password as `MAIL_PASSWORD`

### Step 5: Initialize Database

```bash
python init_db.py
```

This creates:
- SQLite database (`membership.db`)
- All required tables
- Default super admin user

### Step 6: Start the App

```bash
python run.py
```

Open browser: **http://localhost:5000**

---

## Login Flow

1. **First Time:**
   - Email: `admin@membership.local`
   - Click "Send Login Code"
   - Check console/email for OTP code (development mode shows it)
   - Enter code → Login

2. **Add Members:**
   - Go to Admin → Create Members
   - Members get their own login codes

---

## Deployment (Docker)

### Local Docker

```bash
# Build and run
docker-compose up -d

# Check logs
docker-compose logs -f web

# Stop
docker-compose down
```

App runs on `http://localhost:5000`

### Production (AWS/Heroku/VPS)

```bash
# 1. Build image
docker build -t membership-app .

# 2. Push to registry (if using cloud deployment)
docker tag membership-app your-registry/membership-app
docker push your-registry/membership-app

# 3. Run on server
docker run -d \
  -p 5000:5000 \
  -e SECRET_KEY="production-key" \
  -e MAIL_USERNAME="your-email" \
  -e MAIL_PASSWORD="your-password" \
  -e DATABASE_URL="postgresql://user:pass@db:5432/membership" \
  membership-app
```

---

## Key Features Implemented

✅ **Authentication**
- Passwordless OTP login via email
- Session management (12-hour tokens)
- Rate limiting (5 attempts/hour)
- Constant-time password comparison (timing attack prevention)

✅ **User Management**
- Role-based access control (Super Admin, Admin, Manager, Member)
- User profiles
- Activity logging (audit trail)

✅ **Financial Tracking**
- Contribution cycles (fixed and rotating schemes)
- Loan management with approval workflow
- Payment recording and reconciliation
- Penalty tracking for late payments

✅ **Communications**
- Internal messaging system
- Email notifications (OTP, alerts)

✅ **Admin Dashboard**
- Organization overview
- Member management
- Financial reports
- Audit log viewer

---

## API Endpoints

### Authentication
- `POST /api/auth/request-code` - Request OTP
- `POST /api/auth/verify` - Verify OTP & login
- `POST /api/auth/logout` - Logout
- `GET /api/auth/me` - Current user info

### Members
- `GET /api/members` - List members (admin)
- `GET /api/members/<id>` - Get member
- `PUT /api/members/<id>` - Update member
- `POST /api/members` - Create member (admin)

### Contributions
- `GET /api/contributions` - List contributions
- `GET /api/contributions/<id>` - Get contribution
- `GET /api/contributions/cycles` - List cycles
- `POST /api/contributions/cycles` - Create cycle (admin)

### Loans
- `GET /api/loans` - List loans
- `POST /api/loans` - Request loan
- `GET /api/loans/<id>` - Get loan
- `POST /api/loans/<id>/approve` - Approve loan (admin)

### Payments
- `GET /api/payments` - List payments
- `POST /api/payments` - Record payment (admin)
- `POST /api/payments/<id>/reconcile` - Reconcile (admin)

### Messages
- `GET /api/messages` - Inbox
- `POST /api/messages` - Send message
- `POST /api/messages/<id>/mark-read` - Mark read

### Admin
- `GET /api/admin/dashboard` - Organization overview
- `GET /api/admin/members` - Member management
- `GET /api/admin/audit-log` - Activity log

---

## Folder Structure

```
membership-app/
├── app_updated.py          # Flask app factory
├── models.py               # Database models
├── config.py               # Configuration
├── auth.py                 # Authentication logic
├── routes_*.py             # API routes (7 modules)
├── run.py                  # Entry point
├── init_db.py              # Database initialization
├── requirements.txt        # Dependencies
├── Dockerfile              # Docker image
├── docker-compose.yml      # Docker compose
├── .env.example            # Environment template
├── templates/              # HTML templates
│   ├── base.html           # Base layout
│   ├── auth/
│   │   └── login.html      # Login page
│   └── ...                 # Other pages
├── static/                 # CSS, JS, images
├── membership.db           # SQLite database (created)
├── logs/                   # Application logs
└── uploads/                # User file uploads
```

---

## Testing

### Manual Testing

1. **Login Flow**
   - Request OTP for `admin@membership.local`
   - Check console for code (development mode)
   - Verify OTP

2. **Create Member**
   - Admin → Add Member
   - Member receives login code via email

3. **Financial Operations**
   - Create contribution cycle
   - Record payments
   - Request & approve loans

### API Testing (curl)

```bash
# Request OTP
curl -X POST http://localhost:5000/api/auth/request-code \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@membership.local"}'

# Verify OTP
curl -X POST http://localhost:5000/api/auth/verify \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@membership.local","code":"123456","request_id":"..."}'

# Get user
curl -X GET http://localhost:5000/api/auth/me \
  -H "Authorization: Bearer <token>"
```

---

## Common Issues

### "Cannot find email in templates"
- Email service is in progress. Currently logs to console in dev mode.
- In production, configure SMTP credentials in `.env`

### "Session expired"
- Token is valid for 12 hours
- Refresh by logging in again

### "Permission denied"
- Check user role (Admin/Manager/Member)
- Only admins can perform certain actions

### SQLite locked
- Close other connections
- Use WAL mode: `pragma journal_mode=WAL;`

---

## Next Steps (Optional Enhancements)

1. **Email Service** - Configure SMTP for production
2. **Frontend** - Build modern React/Vue UI
3. **Reports** - Generate PDF financial reports
4. **Mobile App** - Native iOS/Android app
5. **Analytics** - Charts and data visualization
6. **Integrations** - Payment gateways, accounting software

---

## Support

- Check logs: `tail -f logs/membership.log`
- Test API health: `curl http://localhost:5000/api/health`
- Database backup: `cp membership.db membership.db.backup`

---

**Built with:** Python + Flask + SQLAlchemy + SQLite  
**Last Updated:** September 2026  
**Version:** 1.0.0
