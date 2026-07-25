# 🏨 Hotel Operations Platform

![Status](https://img.shields.io/badge/status-development-orange)
![Architecture](https://img.shields.io/badge/architecture-clean--architecture-blue)
![Backend](https://img.shields.io/badge/backend-FastAPI-green)
![Frontend](https://img.shields.io/badge/frontend-Next.js-black)
![Database](https://img.shields.io/badge/database-PostgreSQL-blue)

## Overview

**Hotel Operations Platform** یک سامانه هوشمند مدیریت عملیات هتل است که با هدف دیجیتالی‌سازی ارتباط بین مهمانان و واحدهای عملیاتی هتل طراحی شده است.

این سامانه به مهمانان اجازه می‌دهد درخواست‌های خود را به‌صورت آنلاین ثبت کنند و سپس با کمک هوش مصنوعی (AI) درخواست‌ها تحلیل، دسته‌بندی و به واحد مسئول هدایت شوند.

واحدهای مختلف هتل مانند:

- فناوری اطلاعات (IT)
- خانه‌داری (Housekeeping)
- تأسیسات (Maintenance)
- پذیرش (Reception)
- خدمات اتاق (Room Service)

می‌توانند درخواست‌ها را از طریق پنل اختصاصی خود مدیریت کرده، اقدامات لازم را انجام داده و نتیجه را ثبت کنند.

---

# 🎯 Project Vision

هدف پروژه ایجاد یک پلتفرم یکپارچه برای:

- افزایش رضایت مهمان
- کاهش زمان پاسخگویی
- کاهش تماس‌های تلفنی داخلی
- بهبود هماهنگی بین واحدها
- ایجاد داده‌های تحلیلی برای تصمیم‌گیری مدیریتی
- استفاده از هوش مصنوعی برای بهینه‌سازی عملیات هتل

---

# ✨ Main Features

## Guest Portal

مهمانان می‌توانند:

- ورود به سامانه
- مشاهده اطلاعات اقامت
- ثبت درخواست جدید
- مشاهده وضعیت درخواست‌ها
- ارسال پیام
- دریافت اعلان
- ثبت بازخورد

---

## Operator Portal

اپراتورهای واحدها می‌توانند:

- مشاهده درخواست‌های مربوط به واحد خود
- پذیرش درخواست
- تغییر وضعیت Ticket
- ارسال پیام به مهمان
- ثبت نتیجه عملیات
- مدیریت SLA

---

## AI Routing Engine

ماژول هوشمند سامانه:

- تحلیل متن درخواست مهمان
- تشخیص واحد مسئول
- تعیین اولویت
- پیشنهاد مسیر رسیدگی
- یادگیری از اصلاحات اپراتورها

---

## Analytics & Reporting

سیستم گزارش‌گیری شامل:

- داشبورد مدیریتی
- KPIهای عملیاتی
- تحلیل عملکرد واحدها
- گزارش SLA
- تحلیل مشکلات پرتکرار
- تحلیل عملکرد AI

---

# 🏗 System Architecture

سامانه بر اساس معماری:

- Clean Architecture
- Domain Driven Design (DDD)
- Modular Architecture
- API First Design

طراحی شده است.

نمای کلی:

```
Guest
 |
Frontend
 |
API Gateway
 |
Backend Services
 |
--------------------------------
| Ticket | Auth | AI | Reports |
--------------------------------
 |
PostgreSQL
 |
Redis
```

---

# 🛠 Technology Stack

## Backend

| Technology | Purpose |
|---|---|
| Python | Programming Language |
| FastAPI | Backend Framework |
| SQLAlchemy | ORM |
| Alembic | Database Migration |
| Pydantic | Data Validation |

---

## Frontend

| Technology | Purpose |
|---|---|
| Next.js | Web Framework |
| React | UI Library |
| TypeScript | Programming Language |
| Tailwind CSS | Styling |
| shadcn/ui | UI Components |

---

## Infrastructure

| Technology | Purpose |
|---|---|
| Docker | Containerization |
| PostgreSQL | Database |
| Redis | Cache & Queue |
| Nginx | Reverse Proxy |
| GitHub Actions | CI/CD |

---

# 📂 Project Structure

```
hotel-operations-platform/

├── apps/
│   ├── backend/
│   ├── web/
│   └── worker/
│
├── packages/
│
├── infrastructure/
│
├── docs/
│
├── tests/
│
├── docker-compose.yml
│
└── README.md
```

---

# 📚 Documentation

مستندات اصلی پروژه:

| Document | Description |
|---|---|
| SRS.md | Software Requirements Specification |
| Architecture.md | System Architecture |
| Database-Design.md | Database Design |
| API-Design.md | API Documentation |
| Sprint-Plan.md | Development Roadmap |
| project-context.md | AI Development Context |

---

# 🚀 Development Roadmap

## Sprint 1
### Infrastructure, Authentication, Database & CI/CD

Status:
🟡 In Progress

Includes:

- Project initialization
- Docker environment
- Database setup
- Authentication
- CI/CD pipeline


---

## Sprint 2

### Guest Portal & Ticket Creation

Includes:

- Guest dashboard
- Request creation
- Ticket tracking
- Notifications


---

## Sprint 3

### Operator Portal & Ticket Workflow

Includes:

- Department dashboard
- Ticket lifecycle
- SLA management
- Operator workflow


---

## Sprint 4

### AI Routing & Automation

Includes:

- AI classification
- Smart routing
- Notification engine
- Feedback learning


---

## Sprint 5

### Analytics & Optimization

Includes:

- Management dashboards
- Reports
- Performance optimization
- Production readiness

---

# 🔐 Security Principles

سامانه از اصول زیر پیروی می‌کند:

- JWT Authentication
- Role Based Access Control (RBAC)
- Password Hashing
- Audit Logging
- Environment Based Configuration
- Secure API Design

---

# 🧪 Testing

استراتژی تست:

- Unit Testing
- Integration Testing
- API Testing
- End-to-End Testing

هدف:

```
Minimum Coverage: 80%
```

---

# ⚙️ Local Development

## Requirements

- Docker
- Docker Compose
- Git
- Python 3.13+
- Node.js 22+

---

## Run Project

بعد از آماده شدن Sprint 1:

```bash
docker compose up
```

---

# 🤝 Development Guidelines

قوانین توسعه:

- Follow Clean Code principles
- Use Conventional Commits
- Create feature branches
- Write tests for new features
- Update documentation with changes

---

# 🌱 Branch Strategy

```
main

develop

feature/*

bugfix/*

hotfix/*
```

---

# 📌 Current Status

Project Phase:

```
Planning & Initial Development
```

Current Sprint:

```
Sprint 1
```

---

# 👨‍💻 Maintainer

Hotel Operations Platform Team

---

# 📄 License

Private Project

All rights reserved.