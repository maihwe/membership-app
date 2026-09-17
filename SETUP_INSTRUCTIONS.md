# SETUP INSTRUCTIONS - File Organization

## Step 1: Create Root Folder

```bash
mkdir membership-app
cd membership-app
```

---

## Step 2: Copy Root-Level Files

Copy these files directly into `membership-app/`:

```
app_updated.py          (IMPORTANT: Rename to app.py later)
models.py
config.py
auth.py
run.py
init_db.py
requirements.txt
.env.example
Dockerfile
docker-compose.yml
```

**Files to copy:**
- routes_auth.py
- routes_members.py
- routes_contributions.py
- routes_loans.py
- routes_payments.py
- routes_messages.py
- routes_admin.py

**Documentation files:**
- README.md
- QUICKSTART.md
- QUICK_REFERENCE.md
- DELIVERY_INDEX.md
- PROJECT_MANIFEST.md

---

## Step 3: Create Templates Folder

```bash
mkdir -p membership-app/templates/auth
```

---

## Step 4: Move HTML Files to Templates

Copy and rename these files:

```
templates_base.html          → templates/base.html
templates_auth_login.html    → templates/auth/login.html
templates_dashboard.html     → templates/dashboard.html
templates_members.html       → templates/members.html
```

**Example (Linux/Mac):**
```bash
mv templates_base.html templates/base.html
mv templates_auth_login.html templates/auth/login.html
mv templates_dashboard.html templates/dashboard.html
mv templates_members.html templates/members.html
```

**Example (Windows):**
```bash
move templates_base.html templates\base.html
move templates_auth_login.html templates\auth\login.html
move templates_dashboard.html templates\dashboard.html
move templates_members.html templates\members.html
```

---

## Step 5: Create Static Folder

```bash
mkdir -p membership-app/static/css
mkdir -p membership-app/static/js
```

---

## Step 6: CRITICAL - Rename app_updated.py to app.py

**Linux/Mac:**
```bash
cd membership-app
mv app_updated.py app.py
```

**Windows:**
```bash
cd membership-app
ren app_updated.py app.py
```

**Why?** The Flask code imports from `app.py`, not `app_updated.py`

---

## Step 7: Create .env File

```bash
cp .env.example .env
```

Edit `.env` and add your Gmail app password:
```env
SECRET_KEY=generate-a-random-32-char-string
MAIL_PASSWORD=your-gmail-app-password
FLASK_ENV=development
```

---

## Step 8: Verify Folder Structure

Your folder should now look like this:

```
membership-app/
├── app.py                          ← Renamed from app_updated.py
├── models.py
├── config.py
├── auth.py
├── routes_auth.py
├── routes_members.py
├── routes_contributions.py
├── routes_loans.py
├── routes_payments.py
├── routes_messages.py
├── routes_admin.py
├── run.py
├── init_db.py
├── requirements.txt
├── .env                            ← Created from .env.example
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── README.md
├── QUICKSTART.md
├── QUICK_REFERENCE.md
├── DELIVERY_INDEX.md
├── PROJECT_MANIFEST.md
│
├── templates/
│   ├── base.html                   ← Renamed from templates_base.html
│   ├── dashboard.html              ← Renamed from templates_dashboard.html
│   ├── members.html                ← Renamed from templates_members.html
│   └── auth/
│       └── login.html              ← Renamed from templates_auth_login.html
│
└── static/
    ├── css/
    └── js/
```

---

## Step 9: Setup Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
# Linux/Mac:
source venv/bin/activate

# Windows:
venv\Scripts\activate
```

---

## Step 10: Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Step 11: Initialize Database

```bash
python init_db.py
```

You should see:
```
Creating database tables...
✓ Tables created
✓ Created super admin: admin@membership.local

✓ Database initialization complete

Default super admin: admin@membership.local
```

---

## Step 12: Start the App

```bash
python run.py
```

You should see:
```
============================================================
Membership Management System
============================================================
Environment: development
Database: sqlite:///membership.db
Starting on http://localhost:5000
============================================================
```

---

## Step 13: Test Login

1. Open browser: **http://localhost:5000**
2. Enter email: **admin@membership.local**
3. Click "Send Login Code"
4. Check **console output** for OTP code (development mode)
5. Enter the 6-digit code
6. Click "Verify & Login"

---

## ✅ Complete Checklist

- [ ] Created `membership-app/` folder
- [ ] Copied all Python files to root
- [ ] Copied all documentation files to root
- [ ] Created `templates/` folder
- [ ] Created `templates/auth/` subfolder
- [ ] Renamed HTML files and moved to templates/
- [ ] **Renamed `app_updated.py` → `app.py`** ⚠️ CRITICAL
- [ ] Created `static/` folder with `css/` and `js/` subfolders
- [ ] Copied `.env.example` → `.env` and edited it
- [ ] Ran `python init_db.py`
- [ ] Ran `python run.py` and saw startup message
- [ ] Opened browser and tested login

---

## 🆘 If Something Breaks

### "ModuleNotFoundError: No module named 'app'"
**Problem:** `app_updated.py` wasn't renamed to `app.py`  
**Solution:** Rename it: `mv app_updated.py app.py`

### "No such file: templates/base.html"
**Problem:** HTML files weren't moved to templates folder  
**Solution:** Move all template files:
```bash
mv templates_*.html templates/
```

### "No such file: .env"
**Problem:** Didn't create `.env` from `.env.example`  
**Solution:** `cp .env.example .env` then edit it

### "Cannot connect to database"
**Problem:** Database wasn't initialized  
**Solution:** `python init_db.py`

---

## 📊 Final File Count

- ✅ 11 Python files (core app)
- ✅ 7 Python files (routes)
- ✅ 4 HTML templates
- ✅ 6 Configuration files
- ✅ 5 Documentation files
- **Total: 28 files + generated files (db, logs)**

---

## 🎯 You're Ready When

✅ Folder structure matches the diagram above  
✅ `app.py` exists (renamed from `app_updated.py`)  
✅ `templates/` folder exists with HTML files inside  
✅ `.env` file created and edited  
✅ `python run.py` starts without errors  
✅ Browser opens to http://localhost:5000  
✅ Login page shows up  

---

**Once you complete these steps, your app is ready to use!** 🚀
