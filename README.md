# Hotel Client Request Platform — Backend

Django + Django REST Framework backend for managing hotel guest requests.

Runs directly on the host — **no Docker** in this phase.

## Requirements

- Python 3.13
- PostgreSQL 16 (installed locally)

## Setup (Windows)

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# edit .env with your local PostgreSQL credentials
python manage.py migrate
python manage.py runserver
```

## Project layout

```
manage.py
config/
├── settings/
│   ├── base.py
│   ├── development.py
│   └── production.py
├── urls.py
├── wsgi.py
└── asgi.py
apps/
├── core/
├── accounts/
├── guests/
├── rooms/
├── departments/
└── tickets/
requirements/
tests/
.env.example
.gitignore
```

Development follows a phased plan — see the project's implementation
plan for what each phase adds.
