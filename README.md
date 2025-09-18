# Salon Backend

Django REST API

## Prerequisites
- Python 3.12+
- PostgreSQL 13+
- Git

## Quick Start

### 1) Clone
```bash
git clone <YOUR_REPO_URL> salon-backend
cd salon-backend
```

### 2) Create & activate virtual environment
macOS/Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows (PowerShell):
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3) Install dependencies
```bash
pip install -r requirements.txt
```

### 4) Create database (Postgres)
Open `psql` and run:
```bash
createdb (db_name)
```

### 5) Configure environment
Create `.env` at the repo root (or copy from `.env.example` if included)

### 6) Migrate & run
```bash
python manage.py migrate
python manage.py createsuperuser  # optional, for /admin
python manage.py runserver
```

Visit:
- Admin: http://127.0.0.1:8000/admin/
