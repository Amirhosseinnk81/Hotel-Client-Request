# Hotel Client Request Platform

سامانه مدیریت درخواست‌های مهمان هتل (Hotel Client Request Platform) برای ثبت، پیگیری و رسیدگی به درخواست‌های خدماتی و فنی مهمانان.

> **وضعیت فعلی:** MVP کامل — Backend (Django/DRF) و Frontend (Next.js) هر دو تکمیل و تست شده‌اند: پرتال مهمان و داشبورد اپراتور هر دو به‌طور کامل پیاده‌سازی شده‌اند. بخش‌های باز باقی‌مانده صرفاً مربوط به آماده‌سازی برای استقرار Production هستند (نگاه کنید به [Roadmap](#-roadmap)).

---

## 📋 فهرست مطالب

- [معرفی](#-معرفی)
- [هدف پروژه](#-هدف-پروژه)
- [قابلیت‌ها](#-قابلیتها)
- [نقش‌های کاربری](#-نقشهای-کاربری)
- [معماری](#-معماری)
- [Technology Stack](#-technology-stack)
- [پیش‌نیازها](#-پیشنیازها)
- [ساختار پروژه](#-ساختار-پروژه)
- [راه‌اندازی PostgreSQL](#-راهاندازی-postgresql)
- [راه‌اندازی Backend](#-راهاندازی-backend)
- [راه‌اندازی Frontend](#-راهاندازی-frontend)
- [اجرای پروژه](#-اجرای-پروژه)
- [ایجاد داده‌های اولیه](#-ایجاد-دادههای-اولیه)
- [آدرس‌های مهم](#-آدرسهای-مهم)
- [Authentication](#-authentication)
- [API](#-api)
- [Ticket Workflow](#-ticket-workflow)
- [مدل داده](#-مدل-داده)
- [Permission و Authorization](#-permission-و-authorization)
- [تست](#-تست)
- [Django Admin](#-django-admin)
- [Environment Variables](#-environment-variables)
- [امنیت](#-امنیت)
- [عیب‌یابی](#-عیبیابی)
- [وضعیت توسعه](#-وضعیت-توسعه)
- [Roadmap](#-roadmap)
- [تصمیمات معماری](#-تصمیمات-معماری)

---

# 🏨 معرفی

**Hotel Client Request Platform** یک سامانه تحت وب برای مدیریت درخواست‌های مهمانان هتل است.

در فرآیند سنتی، مهمان برای درخواست خدمات یا اعلام مشکل معمولاً با تلفن با پذیرش یا واحد مربوطه تماس می‌گیرد. این روش باعث ایجاد مشکلاتی مانند:

- تماس‌های زیاد با پذیرش
- گم شدن یا فراموش شدن درخواست‌ها
- نبود تاریخچه مناسب
- عدم مشخص بودن مسئول رسیدگی
- نبود امکان پیگیری وضعیت درخواست
- دشواری گزارش‌گیری
- وابستگی زیاد به تماس تلفنی

این سامانه درخواست مهمان را به شکل یک **Ticket** ثبت می‌کند و آن را در اختیار **Department** مربوطه قرار می‌دهد.

---

# 🎯 هدف پروژه

هدف اصلی پروژه ایجاد یک سیستم متمرکز برای:

1. ثبت درخواست مهمان
2. دسته‌بندی درخواست
3. ارسال درخواست به واحد مربوطه
4. تخصیص درخواست به Operator
5. پیگیری وضعیت درخواست
6. ثبت نتیجه رسیدگی
7. نگهداری تاریخچه تغییرات
8. ایجاد یک زیرساخت قابل توسعه برای امکانات آینده

---

# 👥 نقش‌های کاربری

سیستم سه Role اصلی دارد:

| Role | توضیح |
|---|---|
| `GUEST` | مهمان هتل |
| `OPERATOR` | اپراتور یکی از واحدهای هتل |
| `ADMIN` | مدیر/ادمین سیستم |

### Guest

مهمان می‌تواند:

- وارد سامانه شود
- پروفایل خود را مشاهده کند
- درخواست جدید ثبت کند
- درخواست‌های قبلی خود را مشاهده، فیلتر و جستجو کند
- جزئیات درخواست را مشاهده کند
- نتیجه رسیدگی را مشاهده کند

### Operator

اپراتور می‌تواند:

- Ticketهای Department خود را با فیلتر (وضعیت/اولویت) و جستجوی زنده مشاهده کند
- Ticket را به خودش **یا هر اپراتور دیگری در همان واحد** Assign کند
- وضعیت Ticket را طبق ماشین‌حالت مجاز تغییر دهد
- Priority را تغییر دهد
- Resolution ثبت کند (الزامی برای انتقال به وضعیت Resolved)

### Admin

Admin از **Django Admin** استفاده می‌کند (هیچ فرانت‌اند اختصاصی برای Admin ساخته نشده).

امکانات مدیریتی شامل:

- User Management (شامل تعیین Department برای هر Operator)
- Guest Management
- Room Management
- Department Management
- Category Management
- Ticket Management (فیلدهای گردش‌کار مثل status/resolution/assigned_to عمداً read-only هستند تا فقط از مسیر API که قوانین کسب‌وکار را اجرا می‌کند تغییر کنند)
- مشاهده Ticket History

---

# 🧩 قابلیت‌ها

## Guest Portal

- Login با National ID + Room Number (بدون رمز عبور؛ اتاق باید وضعیت `OCCUPIED` داشته باشد)
- مشاهده پروفایل
- ثبت Ticket با انتخاب Department، Category و Priority
- مشاهده لیست Ticketهای خود با فیلتر وضعیت و جستجو
- مشاهده جزئیات Ticket و Resolution

## Operator Dashboard

- ورود با نام کاربری/رمز عبور
- مشاهده Ticketهای Department با فیلتر وضعیت/اولویت و جستجوی debounced
- Assign / Reassign کردن Ticket به هر اپراتور هم‌واحد
- تغییر Status (با رعایت ماشین‌حالت مجاز)
- تغییر Priority
- ثبت Resolution

## Admin

مدیریت کامل داده‌های اصلی از طریق Django Admin.

---

# 🏗 معماری

پروژه یک **Modular Monolith** است — بدون میکروسرویس، بدون Docker.

```text
                    ┌─────────────────────┐
                    │       Browser       │
                    └──────────┬──────────┘
                               │
                  ┌────────────┴────────────┐
                  │                         │
                  ▼                         ▼
          ┌───────────────┐         ┌───────────────┐
          │ Guest Portal  │         │Operator Portal│
          │   Next.js     │         │   Next.js     │
          └───────┬───────┘         └───────┬───────┘
                  │                         │
                  └────────────┬────────────┘
                               │
                            REST API
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Django + DRF      │
                    │      Backend        │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   PostgreSQL 16     │
                    └─────────────────────┘
```

هر دو پرتال (مهمان/اپراتور) در واقع یک پروژه‌ی Next.js واحدند (زیر `frontend/`)، که با Route Groups (`(protected)`) از هم و از صفحات ورود جدا شده‌اند — نه دو اپلیکیشن مجزا.

---

# 🛠 Technology Stack

## Backend

| ابزار | نسخه |
|---|---|
| Python | 3.13+ |
| Django | 5.2 LTS |
| Django REST Framework | 3.16+ |
| djangorestframework-simplejwt | 5.3+ |
| drf-spectacular | 0.27+ (Schema / Swagger / ReDoc) |
| django-filter | 24.2+ |
| django-cors-headers | 4.4+ |
| psycopg (binary) | 3.2+ |
| python-decouple | خواندن `.env` |
| PostgreSQL | 16 |

## Frontend

| ابزار | توضیح |
|---|---|
| Next.js | 16 (App Router) |
| TypeScript | — |
| Tailwind CSS | v4 |
| shadcn/ui | کامپوننت‌های دستی‌نوشته (بدون CLI) |
| react-hook-form + zod | فرم‌ها و اعتبارسنجی |
| @fontsource-variable/vazirmatn | فونت فارسی self-hosted |
| Vitest + React Testing Library | تست خودکار |

بدون Docker، بدون Redis، بدون Celery در این فاز از پروژه.

---

# ✅ پیش‌نیازها

- Python 3.13 یا بالاتر
- PostgreSQL 16 (نصب‌شده و در حال اجرا)
- Node.js (نسخه‌ی سازگار با Next.js 16 و npm)
- npm
- Git

---

# 📁 ساختار پروژه

```text
Hotel-Client-Request/
├── apps/                    # اپ‌های Django
│   ├── core/                #   Health Check، Exception Handler، Permissionهای مشترک
│   ├── accounts/             #   User model، JWT، ورود اپراتور/ادمین
│   ├── guests/                #   پروفایل و ورود مهمان
│   ├── rooms/                 #   مدیریت اتاق
│   ├── departments/           #   واحدهای هتل
│   └── tickets/                #   Category، Ticket، TicketHistory، گردش‌کار
├── config/
│   └── settings/
│       ├── base.py
│       ├── development.py
│       └── production.py
├── tests/                    # تست‌های یکپارچگی (cross-app)
├── requirements/
│   ├── base.txt
│   ├── development.txt
│   └── production.txt
├── docs/                     # مستندات فنی پروژه
│   └── archive/               #   اسناد اولیهٔ ویژن پروژه (منسوخ)
├── frontend/                  # پروژه‌ی Next.js
│   └── src/
│       ├── app/                #   guest/ ، operator/
│       ├── components/
│       ├── contexts/
│       ├── hooks/
│       └── lib/
├── manage.py
├── requirements.txt
└── .env.example
```

بک‌اند در ریشه‌ی ریپازیتوری قرار دارد (بدون پوشه‌ی `backend/` جداگانه)؛ فرانت‌اند در پوشه‌ی `frontend/` کنارش.

---

# 🐘 راه‌اندازی PostgreSQL

۱. مطمئن شوید PostgreSQL 16 نصب و در حال اجراست.

۲. یک دیتابیس و کاربر بسازید (نام‌ها باید با `.env` هماهنگ باشند — بخش [Environment Variables](#-environment-variables)):

```sql
CREATE DATABASE hotel_client_request;
CREATE USER hotel_app WITH PASSWORD 'your-password-here';
GRANT ALL PRIVILEGES ON DATABASE hotel_client_request TO hotel_app;
```

---

# ⚙️ راه‌اندازی Backend

```bash
# ۱. ساخت و فعال‌سازی محیط مجازی
python -m venv venv
venv\Scripts\activate        # ویندوز
# source venv/bin/activate   # مک/لینوکس

# ۲. نصب وابستگی‌ها
pip install -r requirements/development.txt

# ۳. ساخت فایل .env
copy .env.example .env       # ویندوز
# cp .env.example .env       # مک/لینوکس
# سپس مقادیر واقعی (SECRET_KEY، DB_PASSWORD و غیره) را در .env پر کنید

# ۴. اجرای Migration ها
python manage.py migrate

# ۵. ساخت Superuser
python manage.py createsuperuser
```

---

# 🖥 راه‌اندازی Frontend

```bash
cd frontend

# نصب وابستگی‌ها
npm install

# ساخت فایل .env.local (فایل نمونه در ریپو موجود نیست، دستی بسازید)
echo NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api/v1 > .env.local
```

اگر `.env.local` ساخته نشود، فرانت‌اند به‌صورت پیش‌فرض به `http://127.0.0.1:8000/api/v1` وصل می‌شود.

---

# ▶️ اجرای پروژه

در دو ترمینال جدا:

```bash
# ترمینال ۱ — بک‌اند
python manage.py runserver

# ترمینال ۲ — فرانت‌اند
cd frontend
npm run dev
```

---

# 🌱 ایجاد داده‌های اولیه

از طریق Django Admin (`/admin/`) با کاربر Superuser:

1. یک یا چند **Department** بسازید (مثلاً نظافت، فنی)
2. یک یا چند **Category** بسازید (مثلاً خرابی تلویزیون، درخواست حوله)
3. یک **Room** بسازید و وضعیتش را **OCCUPIED** کنید (پیش‌نیاز ورود مهمان)
4. یک **Guest** بسازید و آن را به همان اتاق وصل کنید (کد ملی وارد‌شده برای ورود لازم است)
5. یک کاربر با نقش **OPERATOR** بسازید و حتماً فیلد **Department** آن را پر کنید (بدون این فیلد، اپراتور هیچ تیکتی نمی‌بیند)

---

# 🔗 آدرس‌های مهم

| سرویس | آدرس |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://127.0.0.1:8000/api/v1 |
| Django Admin | http://127.0.0.1:8000/admin/ |
| OpenAPI Schema | http://127.0.0.1:8000/api/schema/ |
| Swagger UI | http://127.0.0.1:8000/api/docs/ |
| ReDoc | http://127.0.0.1:8000/api/redoc/ |

---

# 🔐 Authentication

- احراز هویت مبتنی بر **JWT** (`djangorestframework-simplejwt`)
- **مهمان**: ورود با `national_id` + `room_number` (بدون رمز عبور)؛ اتاق باید وضعیت `OCCUPIED` داشته باشد وگرنه ورود رد می‌شود
- **اپراتور/ادمین**: ورود با `username` + `password` از یک endpoint مشترک
- Access Token شامل claim سفارشی `role` است
- `ROTATE_REFRESH_TOKENS` و `BLACKLIST_AFTER_ROTATION` فعال هستند
- طول عمر توکن‌ها از طریق `.env` قابل تنظیم است (`JWT_ACCESS_TOKEN_LIFETIME`, `JWT_REFRESH_TOKEN_LIFETIME`)
- سمت فرانت‌اند، توکن‌ها در `localStorage` نگه‌داری می‌شوند — به‌عنوان یک تصمیم آگاهانه برای سادگی MVP (بخش [امنیت](#-امنیت) را ببینید)

---

# 📡 API

تمام Endpoint ها نسخه‌بندی‌شده زیر `/api/v1/` هستند.

| Endpoint | متد | توضیح |
|---|---|---|
| `/auth/guest/login/` | POST | ورود مهمان |
| `/auth/operator/login/` | POST | ورود اپراتور/ادمین |
| `/auth/token/refresh/` | POST | رفرش JWT |
| `/guest/profile/` | GET | پروفایل مهمان جاری |
| `/health/` | GET | Health Check (بدون احراز هویت) |
| `/departments/` | GET, POST | لیست (فقط `is_active`) / ساخت (Admin) |
| `/departments/{id}/` | GET, PATCH, PUT, DELETE | جزئیات/ویرایش/حذف (Admin) |
| `/categories/` | GET, POST | مشابه departments |
| `/categories/{id}/` | GET, PATCH, PUT, DELETE | مشابه departments |
| `/rooms/` | GET, POST | مدیریت اتاق (Admin) |
| `/rooms/{id}/` | GET, PATCH, PUT, DELETE | مدیریت اتاق (Admin) |
| `/tickets/` | GET, POST | لیست/ثبت تیکت (فقط تیکت‌های مهمان جاری)، فیلتر `search` |
| `/tickets/{id}/` | GET, PATCH | جزئیات تیکت مهمان (status/resolution فقط‌خواندنی) |
| `/operator/tickets/` | GET | لیست تیکت‌های واحد اپراتور؛ فیلتر `status`, `priority`, `assigned_to`, `search`, `ordering` |
| `/operator/tickets/{id}/` | GET, PATCH | جزئیات/ویرایش (status، priority، resolution، assigned_to) |
| `/operator/tickets/{id}/assign/` | POST | اختصاص به خودِ اپراتور فراخوان؛ status خودکار `IN_PROGRESS` |
| `/operator/colleagues/` | GET | لیست اپراتورهای هم‌واحد (برای اختصاص/تغییر اختصاص) |
| `/schema/` `/docs/` `/redoc/` | GET | مستندات OpenAPI |

فرمت خطای استاندارد برای همه‌ی endpoint ها:

```json
{ "success": false, "message": "...", "errors": {...} }
```

مستندات کامل و تعاملی همیشه در `/api/docs/` در دسترس است.

---

# 🔄 Ticket Workflow

| از وضعیت | به وضعیت‌های مجاز |
|---|---|
| `OPEN` | `IN_PROGRESS`، `CANCELLED` |
| `IN_PROGRESS` | `OPEN` (بازگشایی)، `RESOLVED` |
| `RESOLVED` | — (نهایی) |
| `CANCELLED` | — (نهایی) |

- این قانون هم در سطح مدل (`Ticket.can_transition_to`) و هم در سریالایزر اپراتور اجرا می‌شود
- ثبت `resolution` هنگام انتقال به `RESOLVED` الزامی است؛ `resolved_at` خودکار پر می‌شود
- برای جلوگیری از دور زدن این قانون، فیلدهای `status`, `resolution`, `resolved_at`, `assigned_to` در Django Admin **read-only** هستند — تغییر واقعی وضعیت فقط از مسیر API ممکن است

---

# 🗄 مدل داده

### User
`username`, `password`, `role` (GUEST/OPERATOR/ADMIN), `department` (FK، فقط برای OPERATOR)

### Guest
`user` (OneToOne)، `full_name`، `national_id` (unique)، `phone`، `room` (FK)

### Room
`number` (unique)، `floor`، `status` (AVAILABLE/OCCUPIED/MAINTENANCE)

### Department / Category
`name`، `code`، `is_active`، `created_at`، `updated_at`

### Ticket
`guest` (FK)، `room` (FK, PROTECT — اسنپ‌شات لحظه‌ی ثبت)، `department` (FK, PROTECT)، `category` (FK, PROTECT)، `assigned_to` (FK → User با role=OPERATOR، nullable)، `title`، `description`، `status` (پیش‌فرض OPEN)، `priority` (پیش‌فرض NORMAL)، `resolution`، `created_at`، `updated_at`، `resolved_at`

### TicketHistory
`ticket` (FK)، `user` (FK, nullable)، `action` (CREATED/UPDATED/ASSIGNED/STATUS_CHANGED/PRIORITY_CHANGED)، `old_value`، `new_value`، `created_at`

---

# 🛡 Permission و Authorization

سه کلاس مشترک در `apps/core/permissions.py`:

- **IsGuest** — فقط نقش GUEST
- **IsOperator** — فقط نقش OPERATOR
- **IsAdminRole** — خواندن برای همه‌ی احرازهویت‌شده‌ها، نوشتن فقط ADMIN/superuser

**Object-level:**
- مهمان فقط تیکت‌های خودش را می‌بیند
- اپراتور فقط تیکت‌های Department خودش را می‌بیند
- اختصاص تیکت فقط به اپراتوری با همان Department مجاز است

---

# 🧪 تست

## Backend

۷۵ تست یکپارچگی/واحد (Django Test Runner، نه pytest):

```bash
python manage.py test
```

تست‌ها در دو سطح سازمان‌دهی شده‌اند:
- تست واحد هر اپ، داخل `apps/<app>/tests.py`
- تست یکپارچگی کامل (سناریوی end-to-end مهمان → اپراتور → ادمین)، در `tests/test_mvp_integration.py`

## Frontend

۲۶ تست خودکار با Vitest + React Testing Library:

```bash
cd frontend
npm test          # اجرای یک‌باره
npm run test:watch  # حالت watch
```

پوشش شامل: منطق JWT، کامل‌بودن نگاشت لیبل‌های وضعیت/اولویت، هوک debounce، کامپوننت خطای فرم، و هوک محافظت مسیر (`useRequireRole`).

> تست End-to-End (مثلاً Playwright) هنوز راه‌اندازی نشده؛ تست دستی کامل هر دو پرتال انجام و تأیید شده است.

---

# 🛠 Django Admin

آدرس: `/admin/`

مدل‌های ثبت‌شده: `User` (با فیلد Department)، `Room` (با `list_editable` برای status/floor)، `Department`، `Category`، `Ticket` (با Inline برای `TicketHistory` و فیلدهای گردش‌کار read-only).

---

# 🔧 Environment Variables

فایل نمونه: `.env.example` (در ریشه‌ی ریپو). قبل از اجرا، آن را کپی کرده و مقداردهی کنید:

```bash
copy .env.example .env
```

| متغیر | توضیح |
|---|---|
| `DEBUG` | `True` در dev، **باید `False` باشد در production** |
| `SECRET_KEY` | کلید امنیتی جنگو — در production حتماً یک مقدار تصادفی و طولانی بگذارید |
| `ALLOWED_HOSTS` | دامنه‌های مجاز، جدا‌شده با کاما |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT` | اتصال PostgreSQL |
| `JWT_ACCESS_TOKEN_LIFETIME` | طول عمر Access Token (دقیقه) |
| `JWT_REFRESH_TOKEN_LIFETIME` | طول عمر Refresh Token (روز) |
| `CORS_ALLOWED_ORIGINS` | Originهای مجاز برای فراخوانی API (مثلاً آدرس فرانت‌اند) |
| `DJANGO_LOG_LEVEL` | سطح لاگ (پیش‌فرض `INFO`) |

فرانت‌اند فایل نمونه‌ی جداگانه‌ای ندارد؛ به‌صورت دستی `frontend/.env.local` بسازید:

```
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api/v1
```

---

# 🔒 امنیت

- JWT با `ROTATE_REFRESH_TOKENS` و `BLACKLIST_AFTER_ROTATION`
- تمام کلیدهای خارجی حساس (`room`, `department`, `category` روی Ticket) از `PROTECT` استفاده می‌کنند تا حذف تصادفی داده‌های مرجع، تیکت‌های تاریخی را خراب نکند
- کنترل دسترسی مبتنی بر نقش در سطح API و Object-level (بخش بالا)
- **بدهی فنی شناخته‌شده:** توکن‌های JWT در `localStorage` مرورگر ذخیره می‌شوند، نه httpOnly cookie — این یک تصمیم آگاهانه برای سادگی MVP بوده و پیش از استقرار Production باید بازبینی شود (ریسک XSS)
- `DEBUG=True` و `SECRET_KEY` نمونه در `.env.example` **هرگز** نباید در Production استفاده شوند

---

# 🩺 عیب‌یابی

مشکلاتی که در توسعه واقعاً پیش آمده و راه‌حلشان:

**خطای `Access denied` هنگام حذف `node_modules` در PowerShell**
از `cmd` به‌جای PowerShell استفاده کنید:
```powershell
cmd /c rmdir /s /q node_modules
cmd /c rmdir /s /q .next
```

**خطای `IO error... lockfile` در `next build`**
معمولاً یعنی `npm install` کامل انجام نشده؛ `node_modules` و `.next` را پاک کرده و دوباره `npm install` بزنید. اگر مشکل ماند، آنتی‌ویروس ممکن است پوشه‌ی پروژه را قفل کند.

**خطاهای TypeScript در `.next/dev/types/routes.d.ts` بعد از build**
این فایل خودکار توسط Next.js (typed routes) تولید می‌شود و گاهی خراب می‌شود؛ پاک‌کردن کامل `.next` معمولاً کافی است.

**اپراتور هیچ تیکتی نمی‌بیند**
فیلد `department` کاربر Operator را در Django Admin چک کنید — بدون این فیلد، هیچ تیکتی به او نشان داده نمی‌شود.

**مهمان نمی‌تواند وارد شود**
اتاق مرتبط با آن مهمان باید وضعیت `OCCUPIED` داشته باشد.

---

# 📊 وضعیت توسعه

**Backend** — کامل (Phase 14): مدل کاربر سفارشی، مجوزهای مبتنی بر نقش، ورود مهمان/اپراتور، مدیریت کامل Ticket/Room/Department/Category، Django Admin، مستندات OpenAPI، ۷۵ تست خودکار.

**Frontend** — کامل: پرتال مهمان (ورود، پروفایل، ثبت/لیست/جزئیات تیکت با فیلتر و جستجو) و داشبورد اپراتور (فیلتر/جستجو، اختصاص/تغییر اختصاص، تغییر وضعیت، ثبت Resolution) هر دو تکمیل و تست‌شده‌اند. ۲۶ تست خودکار (Vitest).

---

# 🗺 Roadmap

موارد باز باقی‌مانده (خارج از قابلیت‌های اصلی MVP که همگی تکمیل شده‌اند):

- آماده‌سازی برای استقرار Production (تنظیمات production، دامنه، HTTPS)
- پایپ‌لاین CI/CD
- تست End-to-End در فرانت‌اند
- بازبینی مهاجرت ذخیره‌سازی JWT از `localStorage` به httpOnly cookie

موارد زیر **صراحتاً خارج از دامنه‌ی این پروژه** هستند و برنامه‌ریزی زمانی ندارند: AI Routing، اعلان (SMS/Email/Push)، Analytics پیشرفته، اتصال به PMS/VoIP/IPTV، Redis، Celery، Docker، اپلیکیشن موبایل، معماری Multi-Tenant.

---

# 🧭 تصمیمات معماری

- **Django/DRF به‌جای FastAPI** — یک تلاش موازی و قدیمی‌تر با پشته‌ی FastAPI + Docker کنار گذاشته شد
- **بدون Docker** در فاز فعلی — اجرای مستقیم روی هاست با `venv`
- **PostgreSQL 16** (نه ۱۷) — چون از قبل روی سیستم توسعه نصب بود
- **ورود مهمان با کد ملی + شماره اتاق** (نه کد ملی + تلفن طبق برنامه‌ی اولیه)
- **تنها یک دستیار هوش مصنوعی روی پروژه کار می‌کند** — پس از کشف تناقض کد ناشی از کار موازی دو AI روی یک مخزن
- **ذخیره‌ی JWT در localStorage** برای سادگی MVP، با یادداشت صریح درباره‌ی ریسک امنیتی برای بازبینی در آینده
- **shadcn/ui به‌صورت دستی** (نه CLI) به‌دلیل عدم دسترسی به رجیستری رسمی در محیط توسعه
- **Vazirmatn self-hosted** به‌جای Google Fonts آنلاین