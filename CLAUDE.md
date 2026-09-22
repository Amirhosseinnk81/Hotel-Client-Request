# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

راهنمای کاری این پروژه. مکمل `README.md` است نه جایگزینش — `README.md` برای راه‌اندازی اولیه، این فایل برای قواعد کاری، الگوهای تکرارشونده و باگ‌هایی که قبلاً خورده‌ایم.

> `README.md` تا فاز ۲ به‌روز شده (معماری کوکی JWT، `localhost` به‌جای `127.0.0.1`، تعداد تست‌ها، و فیچرهای PDF/حالت تیره/لاگ اتاق). با این حال هرجا سند و کد اختلاف داشتند، **کد مرجع است** — سند را اصلاح کن، نه برعکس.

## پروژه چیست

**Hotel Client Request Platform** — سامانهٔ مدیریت درخواست‌های مهمانان هتل با سه نقش `GUEST` / `OPERATOR` / `ADMIN`. مهمان درخواست (Ticket) ثبت می‌کند، درخواست به یک Department می‌رود، اپراتور همان واحد آن را برمی‌دارد و تا حل شدن پیگیری می‌کند.

مخزن: `github.com/Amirhosseinnk81/Hotel-Client-Request`

## Tech Stack

| لایه | فناوری |
|---|---|
| Backend | Django 5.2 + DRF 3.16، مونولیت ماژولار (بدون Docker) |
| DB | PostgreSQL 16 — **هرگز SQLite**، حتی برای تست |
| Auth | JWT (`djangorestframework-simplejwt`) — access در حافظهٔ JS، refresh در httpOnly cookie |
| API Docs | drf-spectacular → `Hotel_Client_Request_Platform_API.yaml` |
| PDF | reportlab + arabic-reshaper + python-bidi + jdatetime |
| Frontend | **Next.js 16.3.2** (App Router) + React 19.2 + TypeScript + Tailwind v4 |
| UI Kit | shadcn/ui **دستی‌ساز** (بدون CLI) در `frontend/src/components/ui/` روی Radix |
| فونت | `@fontsource-variable/vazirmatn` در UI؛ TTF کامل Vazirmatn برای PDF |
| تست بک‌اند | Django `TestCase`/`APITestCase` روی PostgreSQL واقعی — **۲۸۲ تست** |
| تست فرانت | Vitest + React Testing Library — **۱۰۵ تست** |
| Deployment | مستقیم روی هاست ویندوز، بدون Docker/Redis/Celery؛ کار زمان‌بندی‌شده با Windows Task Scheduler (`send_pending_sms` هر دقیقه، `snapshot_room_stats` هر شب). هر جریان زندهٔ اپراتور یک thread سرور نگه می‌دارد — بخش «اعلان لحظه‌ای» |

## دستورهای رایج

```bash
# بک‌اند (از ریشهٔ ریپو)
python manage.py migrate
python manage.py runserver localhost:8000      # localhost، نه 127.0.0.1 — بخش «دو تلهٔ همیشگی»
python manage.py seed_demo_data                # دادهٔ دموی فارسی: واحدها، دسته‌ها، اتاق، اپراتور، سرپرست، مهمان
python manage.py seed_demo_data --reset-passwords
python manage.py test                          # کل ۲۸۲ تست
python manage.py test apps.tickets             # فقط یک اپ
python manage.py spectacular --file Hotel_Client_Request_Platform_API.yaml
```

اجرای یک تست منفرد:

```bash
python manage.py test apps.tickets.tests.OperatorTicketAPITests.test_operator_can_cancel_open_ticket
```

```bash
# فرانت‌اند (داخل frontend/)
npm run dev
npm run build
npm run lint
npm test                                       # = vitest run (یک‌باره)
npm run test:watch
npx vitest run src/lib/format.test.ts          # یک فایل تست
npx vitest run -t "relative"                   # فیلتر روی نام تست
```

`DJANGO_SETTINGS_MODULE` پیش‌فرض روی `config.settings.development` است (داخل `manage.py`)؛ لازم نیست دستی ست شود.

## راه‌اندازی — دو تلهٔ همیشگی

**۱. `localhost` در برابر `127.0.0.1`**

کوکی refresh با `SameSite=Lax` ست می‌شود و مرورگر `localhost` و `127.0.0.1` را **دو سایت متفاوت** می‌بیند (نه صرفاً دو پورت). اگر فرانت روی `localhost:3000` باشد و `NEXT_PUBLIC_API_URL` روی `127.0.0.1:8000`، لاگین ظاهراً کار می‌کند ولی refresh در هر ریلود بی‌صدا می‌شکند. پس هر دو طرف `localhost`:

- `python manage.py runserver localhost:8000`
- `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1`

`README.md` هم همین را می‌گوید؛ اگر جایی `127.0.0.1` دیدی، آن سند از قلم افتاده و باید اصلاح شود.

**۲. نام فایل env فرانت‌اند**

در ریپو `frontend/env.local` و `frontend/env.local.example` هستند — بدون نقطهٔ ابتدایی، چون `.env*` در `.gitignore` است. Next.js اینها را نمی‌خواند؛ باید کپی شوند به `frontend/.env.local`.

بک‌اند: `.env.example` → `.env` در ریشه. `SECRET_KEY` و `DB_*` بدون مقدار پیش‌فرض‌اند و نبودشان یعنی خطای بالا‌آمدن. `JWT_COOKIE_SECURE=False` فقط برای dev روی http.

## معماری و ساختار

بک‌اند در **ریشهٔ ریپو** است (پوشهٔ `backend/` جدا وجود ندارد)؛ فرانت‌اند کنارش در `frontend/`.

- `config/settings/` — `base.py` (مشترک) + `development.py` / `production.py`
- `apps/` — هر اپ با الگوی ثابت: `models.py` → `serializers.py` → `views.py` (DRF generics) → `urls.py` → `admin.py` → `tests.py`
  - `core/` — پرمیشن‌های مشترک، `jwt_cookies.py`، `throttling.py`، `exceptions.py`، health check، `seed_demo_data`
  - `accounts/` — User سفارشی (`role`، `department`، `is_supervisor`)، لاگین اپراتور، refresh، logout، وضعیت اپراتور (`/operator/me/status/`، محاسبه‌شده)، و `last_seen_at` (حضور در پنل، برای تخصیص خودکار)
  - `guests/` — Guest و لاگین مهمان
  - `rooms/` — Room و `RoomStatusLog` (لاگ append-only که خودِ `Room.save()` می‌نویسد)
  - `departments/` — CRUD ادمین
  - `tickets/` — هستهٔ پروژه: `Category`، `Ticket`، `TicketHistory`، `TicketNote`، `TicketAttachment`، `QuickRequestTemplate`، و `pdf.py`
  - `it_ops/` — عملیات داخلی واحد IT (`Process`، `Project`، `DepartmentRequest`، `Goal`، `Task`، `RoomDailyStat`) — بخش «IT Ops». **تنها اپی که ViewSet + Router دارد** نه generics؛ عمدی است (شش منبع CRUD هم‌شکل)
  - `notifications/` — صف پیامک مهمان (`SmsMessage`) و درایورهای ارسال — بخش «پیامک»؛ و جریان زندهٔ اپراتور (`stream.py`) — بخش «اعلان لحظه‌ای»
- `tests/test_mvp_integration.py` — سناریوی end-to-end بین اپ‌ها. تست واحد هر اپ داخل خود اپ می‌ماند.
- `frontend/src/` — `app/` با Route Groupهای `guest/(protected)` و `operator/(protected)`، `components/ui/`، `contexts/`، `hooks/`، `lib/api/`

هر دو پرتال مهمان و اپراتور **یک پروژهٔ Next.js واحدند**، نه دو اپلیکیشن جدا.

همهٔ مسیرها زیر `/api/v1/` هستند. فرمت خطای یکسان برای کل API از `apps/core/exceptions.py`:
`{"success": false, "message": "...", "errors": {...}}`

## ماشین‌حالت تیکت — دقیق

منبع حقیقت: `Ticket.ALLOWED_STATUS_TRANSITIONS` در `apps/tickets/models.py`.

```
OPEN         → IN_PROGRESS | CANCELLED
IN_PROGRESS  → RESOLVED | OPEN        ← بازگرداندن به OPEN مجاز است
RESOLVED     → (نهایی)
CANCELLED    → (نهایی)
```

- **`IN_PROGRESS → CANCELLED` مجاز نیست** — بک‌اند با ۴۰۰ ردش می‌کند (`OperatorTicketSerializer.validate_status`).
- پرش `OPEN → RESOLVED` مجاز نیست. ثبت `resolution` هنگام Resolve الزامی است و `resolved_at` خودکار پر می‌شود.
- **Reopen مهمان** عمداً بیرون از این جدول است: مسیر جداگانهٔ `POST /tickets/{id}/reopen/`، فقط از `RESOLVED`، فقط یک‌بار در طول عمر تیکت (نگهبانش `reopened_at` است نه وضعیت فعلی، تا بعد از Resolve دوم هم محدودیت برقرار بماند)، و حداکثر تا ۴۸ ساعت پس از `resolved_at`. منطق در `Ticket.can_guest_reopen`.

سمت فرانت، `allowedNextStatuses` در `frontend/src/lib/ticket-labels.ts` باید **آینهٔ دقیق** همین جدول باشد. قبلاً این دو از هم دررفته بودند (UI روی تیکت `IN_PROGRESS` گزینهٔ Cancel می‌داد که بک‌اند ۴۰۰ می‌کرد، و `IN_PROGRESS → OPEN` را نشان نمی‌داد). الان هم‌راستا شده و تست `ticket-labels.test.ts` جدول بک‌اند را pin می‌کند؛ اگر آن تست قرمز شد، یعنی یکی از دو سمت عوض شده — سمتِ غلط را درست کن، نه انتظار تست را.

## SLA و «معوق»

SLA دو مرحله دارد، هر دو به ازای هر دسته و قابل‌ویرایش از لیست دسته‌ها در Django Admin:

- **حل — `Category.sla_minutes`** (پیش‌فرض ۶۰). **دو کاربرد همزمان** دارد: «زمان تخمینی پاسخ» که به مهمان نشان داده می‌شود، و هایلایت «معوق» در داشبورد اپراتور — عمداً یک عدد، که از هم درنروند. تیکت `RESOLVED`/`CANCELLED` هرگز معوق حساب نمی‌شود (`Ticket.is_overdue`).
- **اولین پاسخ — `Category.response_sla_minutes`** (پیش‌فرض ۱۰، و هرگز بیشتر از `sla_minutes`). مهلتِ «کسی شروعش کند». «شروع» یعنی اولین رفتن به `IN_PROGRESS` که `Ticket.save()` در `first_response_at` ثبت می‌کند — پس PATCH، endpoint تخصیص، کانبان و Django Admin همه حساب می‌شوند — و یک‌بار ثبت می‌شود، حتی اگر تیکت بعداً به OPEN برگردد. تخصیص (دستی یا خودکار) پاسخ حساب **نمی‌شود**. `is_response_overdue` = هنوز OPEN، بدون پاسخ، از مهلت گذشته؛ در پنل برچسب «بدون پاسخ». migration `tickets/0011` این زمان را برای تیکت‌های قدیمی از `TicketHistory` پر کرد.
- هر دو خلاصهٔ آمار حالا `response_overdue_count`، `avg_first_response_minutes`، `response_sla_met_percent` و `resolution_sla_met_percent` هم دارند (`_sla_performance` در `services.py`). درصد وقتی چیزی سررسید نشده `null` است، نه صفر. تیکتی که پیش از شروع لغو شد در هیچ‌کدام حساب نمی‌شود.

## خروجی PDF تیکت

`GET /api/v1/tickets/{id}/export/pdf/` — پاسخ `application/pdf` است نه JSON. دسترسی: هرکس که از قبل از مسیر دیگری هم می‌توانست همان تیکت را ببیند (مهمان صاحب تیکت، اپراتور همان واحد، ادمین). برای عدم تطابق عمداً **۴۰۴ برمی‌گردد نه ۴۰۳**، تا وجود تیکت دیگران لو نرود — هم‌راستا با `GuestTicketDetailView` و `OperatorTicketDetailView`.

منطق تولید در `apps/tickets/pdf.py`. دو نکته که قبلاً وقت زیادی از ما گرفت و در کد فعلی درست پیاده شده — خرابش نکن:

- **فونت:** از فونت «Non-Latin» پکیج Vazirmatn استفاده نکن؛ گلیف حروف لاتین و ارقام ASCII را ندارد و شمارهٔ اتاق و username خالی چاپ می‌شوند. فونت کامل `apps/tickets/assets/fonts/Vazirmatn-{Regular,Bold}.ttf` (لایسنس OFL کنارش هست) درست است.
- **Shaping:** reportlab خودش RTL و جوین حروف را مدیریت نمی‌کند؛ باید با `arabic-reshaper` + `python-bidi` شکل داده شود. **word-wrap باید روی متن unshaped انجام شود و بعد هر خط جداگانه shape شود** — اگر متن shape‌شده را wrap کنی ترتیب حروف به هم می‌ریزد. الگویش در `_wrap_lines` و `_shape` است.

## خلاصهٔ آمار

همان صفحهٔ «Stats Summary» در Django Admin، در پنل اپراتور هم هست: `/operator/summary`.

- **دو endpoint، هرکدام با یک scope ثابت** — نه یک endpoint که بسته به نقش گشاد یا تنگ شود. ادمین: `GET /admin/stats/summary/` (کل هتل، `IsAdminOnly`). اپراتور و سرپرست: `GET /operator/stats/summary/` (فقط واحد خودشان، `IsOperator`). واحد همیشه از `request.user` می‌آید، هرگز از پارامتر کوئری.
- هر دو از `apps/tickets/services.py` می‌خوانند و منطق وضعیت/میانگین/معوق در helperهای مشترک است. خروجی `compute_admin_stats_summary()` دقیقاً حفظ شده، چون صفحهٔ Django Admin هم از همان می‌خواند.
- **`compute_department_stats_summary(None)` عمداً `ValueError` می‌دهد** و ویو برای اپراتورِ بی‌واحد ۴۰۳ برمی‌گرداند. «بدون واحد» هرگز نباید بی‌صدا «همهٔ واحدها» شود — این دقیقاً همان نشتی است که باید جلویش را گرفت. `test_operator_without_a_department_is_refused_not_shown_the_whole_hotel` این را pin می‌کند.
- در نسخهٔ واحد، جدول «به تفکیک واحد» (که فقط یک ردیف می‌شد) جایش را به «بار کاری اپراتورها» داده: کل روستر واحد، حتی اپراتور بی‌کار با ۰، سرپرست‌ها اول. «فعال» یعنی تیکت‌های OPEN/IN_PROGRESS اختصاص‌یافته — دقیقاً همان تعریف «مشغول» (`active_tickets_count` در `services.py`).
- اعداد با `formatNumber` و مدت‌ها با `formatDurationMinutes` از `lib/format.ts`.

## در دسترس بودن خودکار

وضعیت «در دسترس / مشغول» اپراتور **محاسبه می‌شود، ذخیره نمی‌شود**. اپراتور مشغول است تا وقتی دست‌کم یک تیکت OPEN یا IN_PROGRESS در واحد خودش به او اختصاص دارد، و با حل یا لغو آخرینش خودکار در دسترس می‌شود. چند تیکت هم‌زمان مجاز است؛ تا همه تمام نشوند مشغول می‌ماند.

- **یک تعریف، یک جا:** `active_tickets_count()` و `active_ticket_count()` در `apps/tickets/services.py`. دراپ‌داون همکاران، وضعیت خود اپراتور (`GET /operator/me/status/`) و ستون «فعال» خلاصهٔ واحد همه از همین می‌شمارند — نسخهٔ دیگری ننویس.
- چرا محاسبه‌ای: پنج مسیر وضعیت تیکت را عوض می‌کنند (تخصیص، بازتخصیص، Resolve، Cancel، بازگشایی مهمان). یک فیلد ذخیره‌شده باید در همهٔ آن‌ها به‌روز می‌شد و دیر یا زود یکی جا می‌ماند. بازگشایی مهمان تخصیص را نگه می‌دارد، پس همان اپراتور بدون هیچ کد اضافه‌ای دوباره مشغول می‌شود.
- فیلد `User.is_available` و دکمهٔ دستی حذف شده‌اند (migration `accounts/0005`). `PATCH /operator/me/status/` حالا ۴۰۵ می‌گیرد.
- هدر پنل وضعیت را فقط‌خواندنی نشان می‌دهد و در هر جابه‌جایی صفحه و هر تیک polling (۴۵ ثانیه) دوباره می‌خواند.
- `OperatorColleagueSerializer.is_available` از annotation `active_tickets` می‌خواند؛ هر queryset که به آن داده می‌شود باید `.annotate(active_tickets=active_tickets_count())` داشته باشد، وگرنه با AttributeError می‌شکند.

## IT Ops

ماژول `apps/it_ops` برای کار داخلی واحد IT هتل، زیر `/api/v1/it-ops/`. جدول endpointها در README.

- **کارکنان IT نقش جدید نیستند:** اپراتورهای واحدی با کد `settings.IT_DEPARTMENT_CODE` (پیش‌فرض `IT`)، و سرپرست IT همان اپراتور IT با `is_supervisor`. ادمین هم اختیار سرپرست را دارد. کاربر خواسته بود نقش جدیدی اضافه نشود — همان تصمیم «فلگ نه نقش» سمت تیکت.
- **پرمیشن‌ها در `apps/core/permissions.py`:** `is_it_operator` / `is_it_staff` / `is_it_supervisor` و کلاس‌های `IsITStaff` و `CanWorkOnITItem`. هر ViewSet رفتارش را با چند attribute تنظیم می‌کند: `it_staff_can_create`، `it_assignee_field`، `it_supervisor_only_fields`، `it_supervisor_only_values`، `it_assignee_actions`. قاعدهٔ جدید را با همین‌ها بساز، نه با if داخل view.
- **حتی خواندن هم بسته است:** اپراتور هر واحد دیگر (حتی سرپرستش) روی همهٔ endpointها ۴۰۳ می‌گیرد. `IsITStaff` از دیتابیس می‌خواند؛ claim `department_code` در JWT فقط برای نمایش لینک IT در فرانت است (آینه‌اش `lib/it-ops.ts`، که کد `IT` را هاردکد کرده).
- **فقط یک فهرست واحد:** `Process.department` و `DepartmentRequest.requesting_department` به `departments.Department` واقعی FK می‌زنند. نسخهٔ اول IT Ops یک TextChoices جدا از واحدها داشت؛ migrationهای `0002`–`0004` کدها را به ردیف واقعی نگاشت کردند (`F_AND_B`→`ROOM_SERVICE`، بی‌تطابق→`NULL`). این migrationها عمداً سه فایل‌اند: PostgreSQL وقتی ردیف‌های همان جدول در همان تراکنش آپدیت شده باشند `ALTER TABLE` را با «pending trigger events» رد می‌کند.
- **`next_due_at` خودکار است** و منطقش در `Process.save()` است (مثل `Room.save()`، نه signal): وقتی خالی باشد، `last_done_at` جابه‌جا شود، یا `frequency` عوض شود، دوباره حساب می‌شود؛ جابه‌جایی دستی بقیهٔ وقت‌ها حفظ می‌شود. فرایند `NONE` هرگز دست نمی‌خورد. `_add_months` طول ماه را رعایت می‌کند (بدون وابستگی `dateutil`).
- **`RoomDailyStat` ورودی دستی نیست:** `services.snapshot_room_stats` امروز را از `Room.status` زنده و روز گذشته را از `RoomStatusLog` بازسازی می‌کند. ViewSetش `ReadOnly` است (POST روی لیست ۴۰۵)، و ردیف تازه از اکشن `snapshot/` (سرپرست) یا دستور شبانهٔ `snapshot_room_stats` در Task Scheduler می‌آید. داشبورد `today/` اشغال امروز را زنده حساب می‌کند نه از آخرین ردیف ذخیره‌شده.
- **اولویت رشته‌ای را `order_by("-priority")` نکن** — الفبایی می‌شود (MEDIUM اول، CRITICAL آخر). از `priority_rank()` در `it_ops/models.py` استفاده کن. تست `test_list_puts_the_most_urgent_first_not_alphabetical` این را pin می‌کند.
- فیلترها با django-filter در `it_ops/filters.py`؛ تاریخ خراب ۴۰۰ می‌گیرد نه ۵۰۰.
- **واحدهای دیگر هم به IT درخواست می‌دهند**، ولی نه از مسیرهای IT: `/it-ops/outgoing-requests/` (`OutgoingITRequestViewSet`) با پرمیشن `IsOperatorWithDepartment`. هر اپراتورِ واحددار فقط درخواست‌های واحد خودش را می‌بیند، واحد و درخواست‌دهنده همیشه از `request.user` می‌آیند نه از بدنه، و بعد از ثبت نمی‌تواند تغییرش دهد (PATCH/DELETE ۴۰۵) — وضعیت و مسئول کار IT است. `requested_by` روی `DepartmentRequest` را فقط همین ویو پر می‌کند. صفحهٔ فرانتش `/operator/it-requests` است.
- **فرم‌های صفحهٔ IT** (`components/it-ops/item-dialog.tsx` + `resource-panel.tsx`) یک دیالوگ مشترک‌اند که با field spec کار می‌کنند. دو قاعده که شکستنشان ۴۰۳ می‌سازد: در ویرایش **فقط فیلدهای تغییرکرده** فرستاده می‌شوند (`changedFields`) — چون `CanWorkOnITItem` صرفِ حضور یک فیلد سرپرستی در بدنه را رد می‌کند، حتی با مقدار دست‌نخورده؛ و فیلدهایی که بیننده اجازه‌شان را ندارد اصلاً نمایش داده نمی‌شوند (`isItFieldEditable`). در ساخت، فیلد خالی فرستاده نمی‌شود تا پیش‌فرض سرور اعمال شود.
- `DepartmentRequestSerializer` در schema با نام `ITDepartmentRequest` است، چون `DepartmentSerializer` با `COMPONENT_SPLIT_REQUEST` خودش کامپوننتی به نام `DepartmentRequest` می‌سازد. enumهای وضعیت/اولویت IT هم در `ENUM_NAME_OVERRIDES` نام گرفته‌اند؛ اگر enum تازه‌ای با نام تکراری اضافه شد، spectacular اسم هش‌دار می‌سازد — همان‌جا نامش بده.

## تخصیص خودکار

الهام از Odoo Helpdesk («بار کاری متوازن»). هر تیکت تازهٔ مهمان — اگر `Department.auto_assign` روشن باشد (پیش‌فرض خاموش؛ از لیست واحدها در Django Admin، و در دادهٔ دمو روشن) — مستقیم به کم‌کارترین اپراتور **حاضر** همان واحد می‌رسد: `auto_assign` / `pick_auto_assignee` در `apps/tickets/services.py`، صدا زده از `GuestTicketListCreateView.perform_create`.

- **«حاضر» یعنی پنلش باز است**، نه «در شیفت» — شیفت در سیستم وجود ندارد و دادن تیکت به کسی که رفته خانه بدتر از گذاشتنش برای سرپرست است. `User.last_seen_at` را ضربان جریان زنده و `GET /operator/me/status/` به‌روز می‌کنند؛ پنجره `OPERATOR_PRESENCE_SECONDS` (پیش‌فرض ۱۲۰). کسی حاضر نیست ← تیکت بی‌صاحب می‌ماند مثل قبل.
- ترتیب: کمترین تیکت فعال (همان تعریف «مشغول»)، بعد اپراتور عادی پیش از سرپرست، بعد نام کاربری.
- تیکت **OPEN می‌ماند** — اپراتور هنوز باید شروعش کند، که همان اولین پاسخ SLA است. ثبت در تایم‌لاین: `ASSIGNED` با `user=None` (سیستم).
- سرپرست همچنان می‌تواند بازتخصیص دهد؛ تیکتِ از قبل تخصیص‌یافته دست نمی‌خورد.

## اعلان لحظه‌ای (Stage 3.2)

`GET /api/v1/operator/events/` — جریان Server-Sent Events؛ جای polling زنگوله را گرفته، نه کنارش (فراخوانی `getNewTicketCount` از فرانت حذف شد؛ endpoint `new-count/` بک‌اند برای سازگاری مانده). منطق در `apps/notifications/stream.py`، کلاینت در `frontend/src/lib/realtime.ts`.

- رویدادها: `ticket.created` (تیکت تازه در واحد)، `ticket.assigned` (به من سپرده شد — از `TicketHistory`)، `heartbeat` (هر `SSE_HEARTBEAT_SECONDS`: وضعیت مشغول/در دسترس من + ثبت حضور)، `reconnect` (جریان بعد از `SSE_MAX_SECONDS` تمام می‌شود). هر رویداد `cursor` دارد و کلاینت در اتصال دوباره `?after_ticket=&after_history=` می‌فرستد تا چیزی جا نماند.
- **چرا SSE و نه Channels:** یک‌طرفه است، روی همین سرور WSGI بدون Redis و بدون ASGI کار می‌کند. سرور هر `SSE_POLL_SECONDS` با cursor شناسه دیتابیس را نگاه می‌کند — ساده، و بعد از ری‌استارت هم درست.
- **چرا `fetch` و نه `EventSource`:** `EventSource` هدر Authorization نمی‌فرستد؛ توکن نباید در URL یا کوکی خواندنی برود. `getFreshAccessToken()` در `client.ts` توکن را فقط برای هدر برمی‌گرداند و جای دیگری نگهش نمی‌دارد — چهار بند بخش امنیت دست‌نخورده‌اند. پایان دوره‌ای جریان باعث می‌شود هر اتصال تازه با توکن تازه برود.
- `renderer_classes` شامل `EventStreamRenderer` است تا `Accept: text/event-stream` با ۴۰۶ رد نشود.
- **هزینه:** هر جریان باز یک thread سرور را تا `SSE_MAX_SECONDS` نگه می‌دارد. سرور production باید thread pool به اندازهٔ اپراتورهای هم‌زمان به‌علاوهٔ حاشیه داشته باشد — در تصمیم استقرار لحاظ شود.
- فرانت (`layout.tsx` اپراتور): تیکت تازه ← شمارندهٔ زنگوله، صدای کوتاه (`lib/chime.ts`، Web Audio، بدون فایل صوتی)، toast، و رویداد `TICKET_EVENT` که لیست را دوباره می‌خواند. صدا فقط بعد از اولین کلیک کار می‌کند (قانون مرورگر) و دکمهٔ بی‌صدا دارد. ادمین جریان ندارد (۴۰۳ ← کلاینت برای همیشه قطع می‌کند).
- تست generator با `sleep`/`clock` جعلی بدون انتظار واقعی اجرا می‌شود (`apps/notifications/tests_stream.py`).

## پیامک (Stage 3.1)

`apps/notifications`. ثبت تیکت و Resolve شدنش به مهمان پیامک می‌دهد، **بدون Celery و Redis**: تصمیم کاربر «صف در PostgreSQL» بود.

- **جریان تیکت فقط یک ردیف در صف می‌نویسد** (`queue_ticket_sms`، صدا زده از `GuestTicketListCreateView.perform_create` و `OperatorTicketDetailView.perform_update` وقتی وضعیت به RESOLVED می‌رود). ارسال واقعی بعداً و بیرون از request در `manage.py send_pending_sms` است که Task Scheduler ویندوز هر دقیقه اجرایش می‌کند. پس سرویس پیامکِ کند یا قطع هرگز ثبت/Resolve را کند، خراب یا rollback نمی‌کند — شرط DoD.
- `queue_ticket_sms` **هرگز raise نمی‌کند** و در savepoint خودش می‌نویسد؛ خطای دیتابیس هم تراکنش بیرونی را آلوده نمی‌کند. `test_the_ticket_is_created_even_if_queueing_the_sms_blows_up` این را pin می‌کند. مهمان بی‌شماره و `SMS_ENABLED=False` بی‌صدا رد می‌شوند.
- ارسال: `select_for_update(skip_locked=True)`، پس دو اجرای هم‌پوشان یک پیامک را دو بار نمی‌فرستند. شکست ← backoff نمایی (۱، ۲، ۴… دقیقه، سقف یک ساعت) تا `SMS_MAX_ATTEMPTS` و بعد `FAILED`. در Django Admin اکشن «Retry» هست.
- درایور با `SMS_BACKEND` (مثل `EMAIL_BACKEND` جنگو). پیش‌فرض `ConsoleSmsBackend` است: چیزی نمی‌فرستد، فقط لاگ می‌کند و موفق برمی‌گرداند. `KavenegarSmsBackend` آماده است (urllib، بدون وابستگی) — با `SMS_API_KEY` و `SMS_SENDER` در `.env` فعال می‌شود. عوض‌کردن سرویس یعنی یک کلاس تازه، نه معماری تازه.
- متن پیامک همیشه فارسی است؛ سرور زبان مهمان را نمی‌داند (انتخاب زبان فقط در مرورگر است).

## چندزبانگی پرتال مهمان

فقط `/guest/*` فارسی/انگلیسی است؛ پنل اپراتور عمداً فقط فارسی می‌ماند (کارکنان ایرانی‌اند).

- **بدون کتابخانه:** دیکشنری تایپ‌شده در `lib/i18n.ts`. `en` از نوع `Record<MessageKey, string>` است، پس کلیدی که به `fa` اضافه و در `en` فراموش شود خطای کامپایل است. `i18n.test.ts` یکی‌بودن کلیدها و placeholderهای `{…}` در دو زبان را pin می‌کند.
- `LocaleProvider` (`contexts/locale-context.tsx`) در `app/guest/layout.tsx` کل `/guest` را می‌پوشاند و `lang`/`dir` روی `<html>` را عوض می‌کند و موقع خروج به fa/rtl برمی‌گرداند. انتخاب در `localStorage` (`guest-locale`). اسکریپت init در `app/layout.tsx` انتخاب انگلیسی را پیش از اولین paint اعمال می‌کند تا RTL فلش نزند؛ `LocaleProvider` تا خواندن انتخاب ذخیره‌شده به `dir` دست نمی‌زند.
- کامپوننت‌های مشترک با پنل اپراتور (`RelativeTime`، دکمهٔ PDF، ThemeToggle، دکمهٔ بستن Dialog) از `useOptionalLocale()` استفاده می‌کنند: داخل پرتال مهمان زبان مهمان، بیرونش فارسی. `lib/format.ts` پارامتر اختیاری `locale` دارد (پیش‌فرض `fa`؛ `en` = تقویم میلادی و ارقام لاتین).
- آیکون‌های جهت‌دار (برگشت، رفتن) با `ltr:rotate-180` برعکس می‌شوند. کلاس‌های فیزیکی (`left-4`) جایشان را به منطقی (`end-4`) داده‌اند.
- **ترجمه نمی‌شوند:** داده‌ای که هتل وارد کرده (نام واحد، دسته، قالب درخواست سریع، resolution اپراتور) و پیام خطای API. برای ترجمهٔ داده، فیلد `name_en` روی مدل لازم است — تصمیم جدا.

## حالت آفلاین اپراتور

تصمیم کاربر: «خواندنی + صف اقدامات». منطق در `lib/offline.ts`، نمایش در `components/offline-indicator.tsx`.

- **خواندن:** GETهای اپراتور (لیست، جزئیات، تایم‌لاین، همکاران، وضعیت خودم) از `readThrough` رد می‌شوند: پاسخ موفق در `sessionStorage` نگه داشته می‌شود و وقتی شبکه قطع است (`TypeError` از fetch) همان برمی‌گردد. خطای سرور (۴۰۳، ۴۰۴…) هرگز پشت کش پنهان نمی‌شود.
- **نوشتن:** فقط تغییر وضعیت (با resolution) و یادداشت داخلی صف می‌شوند — در `localStorage`، به ازای هر کاربر. تخصیص، اولویت و عکس شبکه لازم دارند. `updateOperatorTicket` / `addOperatorTicketNote` به‌جای خطای شبکه `QueuedOfflineError` می‌دهند (با تیکت خوش‌بینانه)؛ هر call site جدیدی که وضعیت یا یادداشت ثبت می‌کند باید اول این را بگیرد، وگرنه «در صف ماند» را به‌شکل خطا نشان می‌دهد.
- **بازپخش:** `flushQueue` به ترتیب، با `directOperatorApi` (بدون کش و بدون صف — وگرنه شکستِ بازپخش خودش را دوباره صف می‌کرد). پیش از هر تغییر وضعیت تیکت را دوباره می‌خواند و اگر `updated_at` با نسخه‌ای که اپراتور دیده بود فرق کند، **اقدام را دور می‌ریزد و به‌عنوان تعارض اعلام می‌کند** تا کار همکار بازنویسی نشود. تغییرات خودِ صف روی همان تیکت تعارض حساب نمی‌شوند. خطای شبکه وسط کار ← توقف و نگه‌داشتن بقیه؛ رد سرور ← دور ریختن و اعلام. بعد از بازپخش `OFFLINE_SYNCED_EVENT` صفحه‌ها را وادار به خواندن دوباره می‌کند.
- **توکن ذخیره نمی‌شود — عمداً.** آفلاین فقط «قطع اینترنت وسط کار» را پوشش می‌دهد. ریلود در حالت آفلاین: `restoreSession()` حالا `"offline"` برمی‌گرداند، `AuthProvider` فلگ `isOfflineUnverified` می‌گذارد، `useRequireRole` به لاگین ری‌دایرکت نمی‌کند و پنل پیام «آفلاین هستید» نشان می‌دهد؛ با رویداد `online` یا هر ۱۵ ثانیه دوباره تلاش می‌کند (قطع‌بودن سرور رویداد `online` نمی‌دهد).
- خروج (`logout`) همهٔ کش و صف را پاک می‌کند (`clearOfflineData`).
- **Service worker** (`public/sw.js`، فقط build تولیدی، ثبت از layout اپراتور) فقط پوستهٔ اپ را کش می‌کند: `/_next/static` کش‌اول، صفحه‌ها و payloadهای RSC شبکه‌اول. به APIها (origin دیگر) دست نمی‌زند — کش‌کردن API در Cache Storage دادهٔ مهمان‌ها را بعد از خروج روی دستگاه جا می‌گذاشت. `next.config.ts` برای `/sw.js` هدر `no-cache` می‌گذارد. `app/manifest.ts` نصب PWA را ممکن می‌کند.

## Dark Mode

کلاس‌محور است: `ThemeProvider` در `frontend/src/contexts/theme-context.tsx` کلاس `dark` را روی `<html>` می‌گذارد و انتخاب کاربر را در `localStorage` نگه می‌دارد. در Tailwind v4 با `@custom-variant dark (&:is(.dark *))` در `globals.css` وصل شده. پالت تیره همان هویت قهوه‌ای/برنزی را نگه می‌دارد، نه یک وارونه‌سازی خاکستری/مشکی.

## زبان بصری — قواعدی که نباید بشکنند

پالت و تایپوگرافی از روی `arazhotels.com` (سایت هتل آراز) نمونه‌برداری شده تا اپ هم‌خانوادهٔ برند هتل باشد. همه‌چیز در `frontend/src/app/globals.css` توکن‌بندی شده. سه قاعده که شکستنشان کل کار را خنثی می‌کند:

- **برنزی (`--accent`) هرگز رنگ متن یا پرکنندهٔ دکمه نیست.** `#c59d72` روی سفید فقط حدود ۲.۳:۱ کنتراست دارد و رد می‌شود. برای هر چیزی که متن حمل می‌کند از `--primary` (قهوه‌ای `#7c5f47`، حدود ۵.۷:۱) استفاده کن. برنزی فقط برای خط حائل، هاور و نشانه‌های کوچک — الگویش `.rule-accent`. در حالت تیره این محدودیت برداشته می‌شود چون برنزی روی زمینهٔ `#141617` کنتراست کافی پیدا می‌کند.
- **مشکی خالص برای متن ممنوع.** حتی تیترها `#4d4d4d` هستند (حدود ۸.۴:۱، AAA). مشکی خالص کنار این پالت ارزان به نظر می‌رسد.
- **تیترها سبک‌اند نه ضخیم.** از `.display-1/2/3` استفاده کن (وزن ۴۰۰ با tracking منفی)، نه `font-semibold`. تأکید از اندازه و فضای اطراف می‌آید. بدنه برعکس است: ارتفاع خط ۱.۷۲ با tracking مثبت. همین تضاد است که حس «بی‌عجله» می‌دهد.

`--radius: 0` است و همهٔ اجزا گوشه‌تیزند. سایه فقط روی عناصر شناور (دیالوگ، دراپ‌داون، توست، تولتیپ) مانده که واقعاً بالای صفحه شناورند؛ کارت‌ها و دکمه‌ها با خط حائل یک‌پیکسلی تفکیک می‌شوند نه سایه. `rounded-full` فقط برای نقطه‌های واقعی (وضعیت در دسترس، گرهٔ تایم‌لاین) مجاز است.

فونت AbarMid که سایت آراز استفاده می‌کند تجاری است و **برنداشتیم**؛ Vazirmatn با تنظیم وزن و tracking همان حس را می‌دهد.

## تاریخچهٔ وضعیت اتاق

`RoomStatusLog` را خودِ `Room.save()` می‌نویسد — append-only، هیچ‌جا آپدیت یا حذف نمی‌شود. خواندنش از `GET /api/v1/rooms/{id}/status-logs/`. سریالایزرش عمداً فقط‌خواندنی است.

## سطح دسترسی اپراتورها

سه سطح. سرپرست یک **فلگ** روی User است (`is_supervisor`)، نه نقش جدید — تا همهٔ چک‌های موجود `role == "OPERATOR"` (scoping واحد، لیست همکاران، اینکه تیکت به چه کسی قابل تخصیص است) بدون تغییر کار کنند و سرپرست همچنان خودش هم تیکت‌گیر باشد.

| | دیدن تیکت‌های واحد | وضعیت و resolution | اولویت و تخصیص |
|---|---|---|---|
| اپراتور عادی | همه | فقط تیکت‌های خودش | ✗ |
| سرپرست | همه | همهٔ تیکت‌های واحد | ✓ |
| ادمین | — (فقط خلاصهٔ کل هتل) | ✗ | ✗ |

- پیاده‌سازی: `IsSupervisor` و `CanWorkOnOperatorTicket` در `apps/core/permissions.py`. آینهٔ فرانتش `lib/ticket-permissions.ts` است (با تست خودش) و فقط تصمیم می‌گیرد کدام کنترل نمایش داده شود.
- **هرگز برای مجوز به claim توکن اعتماد نکن.** `is_supervisor` در JWT فقط راهنمای UI است: refresh rotation claimها را عیناً جلو می‌برد، پس سرپرستِ تنزل‌یافته تا ورود بعدی claim قدیمی را دارد. `IsSupervisor` همیشه از `request.user` (دیتابیس) می‌خواند و `test_demoting_a_supervisor_takes_effect_despite_a_stale_token_claim` این را pin می‌کند.
- عکس نتیجه همچنان فقط کار مسئول تیکت است، حتی وقتی سرپرست Resolve می‌کند؛ فرانت ورودی عکس را برای غیرمسئول نشان نمی‌دهد.
- تیکت بسته (RESOLVED/CANCELLED) از هیچ مسیری قابل تخصیص نیست. endpoint تخصیص قبلاً بی‌شرط `IN_PROGRESS` می‌گذاشت و تیکت نهایی را دوباره باز می‌کرد؛ حالا از `can_transition_to` عبور می‌کند.
- **بعد از migration `accounts/0004` همهٔ اپراتورهای موجود عادی‌اند** و هیچ‌کس نمی‌تواند تخصیص دهد تا ادمین در Django Admin تیک `is_supervisor` را برای دست‌کم یک نفر در هر واحد بزند. `seed_demo_data` برای هر واحد یک حساب `sup_*` می‌سازد.
- ادمین در پنل اپراتور تیکت نمی‌بیند (همهٔ endpointهای تیکت اپراتور `IsOperator` دارند و ادمین واحد ندارد). صفحهٔ اول او در پنل `/operator/summary` است — خلاصهٔ کل هتل — و `/operator` خودکار به آنجا هدایتش می‌کند. زنگوله و polling تیکت جدید هم برای ادمین خاموش است.
- در `OperatorTicketAPITests` اپراتور نمونه سرپرست است، چون آن تست‌ها ماشین‌حالت و اعتبارسنجی را می‌سنجند نه سطح دسترسی. سطح دسترسی کلاس خودش را دارد: `OperatorAccessLevelTests`.

## الگوهای جاافتاده — اینها را تکرار کن، چیز نو اختراع نکن

**بک‌اند**

- پرمیشن‌ها فقط از `apps/core/permissions.py`. تفاوت حیاتی: `IsAdminRole` نوشتن را به ادمین محدود می‌کند ولی **خواندن را برای هر کاربر لاگین‌شده باز می‌گذارد**؛ `IsAdminOnly` حتی GET را هم می‌بندد. هر endpointی که دادهٔ بین‌واحدی می‌دهد (مثل `admin/stats/summary/`) باید `IsAdminOnly` باشد — اشتباه گرفتن این دو یعنی افشای دادهٔ واحدهای دیگر به اپراتور.
- تغییر مدل → `makemigrations <app>`.
- تغییر API → دوباره `spectacular` بزن. فایل YAML دستی ادیت نمی‌شود.
- منطق غیر-CRUD برود در `services.py` (نمونه: `compute_admin_stats_summary`)، نه داخل view.
- همهٔ اپ‌ها `app_name` دارند و تست‌های هر اپ آدرس‌ها را با `reverse("<app>:<name>")` می‌سازند — از جمله `apps/tickets/tests.py` که قبلاً رشتهٔ ثابت می‌نوشت و حالا یکدست شده. تست جدید هم همین‌طور.
- **استثنای عمدی:** `tests/test_mvp_integration.py` آدرس‌های تیکت و راه‌اندازی را به‌صورت مسیر ثابت نگه می‌دارد. `lib/api/client.ts` فرانت همین مسیرها را هاردکد کرده؛ اگر مسیری تغییر نام بدهد، `reverse()` بی‌صدا دنبالش می‌رود ولی کلاینت واقعی می‌شکند. آن فایل قناری قرارداد آدرس فرانت است — «درستش» نکن و به `reverse()` تبدیلش نکن.

**فرانت‌اند**

- فراخوانی API فقط از `src/lib/api/client.ts` با تایپ از `src/lib/api/types.ts`.
- بازخورد عملیات فقط با `toast()` از `src/hooks/use-toast.ts` — نه پیام ثابت روی صفحه.
- Loading فقط `<Skeleton />` — نه متن «در حال بارگذاری…».
- اکشن برگشت‌ناپذیر (Cancel، Resolve) حتماً با `<Dialog>` تأیید شود. `resolve-ticket-dialog.tsx` عمداً بین نمای لیست و کانبان مشترک است.
- تاریخ/زمان فقط از `lib/format.ts`؛ `Intl.DateTimeFormat` را داخل صفحه‌ها کپی نکن.
- برچسب و رنگ وضعیت/اولویت فقط از `lib/ticket-labels.ts`.
- همه‌چیز فارسی و RTL. کامپوننت UI جدید را با CLI شادسی‌ان نصب نکن؛ دستی روی Radix بساز.

**Next.js 16**

`frontend/AGENTS.md` (و `frontend/CLAUDE.md` که فقط به آن ارجاع می‌دهد) را خود `next dev` تولید و بازنویسی می‌کند. حکمش این است: این نسخه با چیزی که در آموزش دیده‌ای فرق دارد — پیش از نوشتن کد Next، راهنمای مربوطه را از `frontend/node_modules/next/dist/docs/` بخوان. اگر این بلوک در diff ظاهر شد پاکش نکن؛ همراه کار خودت کامیتش کن.

## امنیت — این معماری را نشکن

مهاجرت از localStorage به httpOnly cookie انجام شده است:

- **refresh token** فقط با `Set-Cookie` می‌رود (httpOnly، `SameSite=Lax`، `path=/api/v1/auth/`) و هرگز در بدنهٔ هیچ پاسخ JSON نیست.
- **access token** فقط در یک متغیر ماژولی داخل `client.ts` زندگی می‌کند — نه localStorage، نه کوکی خواندنی با JS. بعد از ریلود با `restoreSession()` از روی کوکی بازسازی می‌شود.
- `credentials: "include"` روی مسیرهای auth الزامی است، و `CORS_ALLOWED_ORIGINS` باید لیست صریح بماند (هرگز `*`) وگرنه مرورگر کوکی را نمی‌پذیرد.

با هر دست‌کاری در `AuthProvider` یا `client.ts` هر چهار بند را دوباره چک کن.

حالت آفلاین اپراتور هیچ‌کدام از این‌ها را عوض نکرده: توکن همچنان فقط در حافظه است. آنچه آفلاین ذخیره می‌شود دادهٔ تیکت (در `sessionStorage`) و صف اقدامات (در `localStorage`) است، هر دو با خروج پاک می‌شوند — بخش «حالت آفلاین اپراتور».

لاگین مهمان رمز عبور ندارد، پس تنها ترمز حدس‌زدن `national_id` / `room_number` همان throttle است: `guest_login`، پیش‌فرض `10/min`، تنظیم‌شدنی با `GUEST_LOGIN_THROTTLE_RATE`.

## باگ‌های قبلی — دوباره تکرار نکن

- **آپلود فایل در `apiFetch`:** پیش از ست‌کردن `Content-Type: application/json` حتماً `instanceof FormData` چک شود، وگرنه آپلود چندبخشی بی‌صدا خراب می‌شود. الان درست است — خرابش نکن.
- **`read_only_fields = fields`:** اگر سریالایزر قرار است داده هم بپذیرد، این باعث می‌شود ورودی بی‌صدا و بدون خطای validation دور ریخته شود. فقط برای سریالایزرهای صرفاً خواندنی درست است (مثل `RoomStatusLogSerializer`).
- **Pagination:** `PageNumberPagination` با `PAGE_SIZE=10` به‌صورت پیش‌فرض روی همهٔ لیست‌هاست. تستی که فرض کند `response.data` مستقیماً لیست است بی‌صدا فیل می‌شود؛ باید `response.data["results"]` باز شود.
- **حذف پوشهٔ عمیق در ویندوز:** `cmd /c rmdir /s /q node_modules` — نه `Remove-Item` در PowerShell (قفل‌شدن فایل).
- **کش `.next`:** بعد از تغییر ساختاری، اگر خطای عجیب TypeScript روی `routes.d.ts` دیدی، `.next` را کامل پاک کن.
- **تست زمان‌محور روی ویندوز:** ساعت ویندوز حدود هر ۱۵ میلی‌ثانیه تیک می‌خورد، پس `since = timezone.now()` و `created_at` ردیفی که بلافاصله بعدش ساخته می‌شود می‌توانند دقیقاً برابر باشند و شرط `>` فیل شود. در تست یک فاصلهٔ صریح بگذار (`- timedelta(seconds=1)`)؛ `test_new_count_reflects_tickets_created_after_since` یک‌بار دقیقاً همین‌طور فلیکی بود.
- **`swagger_fake_view`:** هر `get_queryset` که از `request.user` فیلتر می‌گیرد باید اول `getattr(self, "swagger_fake_view", False)` را چک کند و `.none()` برگرداند؛ وگرنه `spectacular` با AnonymousUser می‌شکند و هشدار می‌دهد (نمونه: `OutgoingITRequestViewSet`).
- **مرج دستی:** وقتی Amirhossein خودش یک Stage را پیاده می‌کند، فیچرهای تأییدشدهٔ قبلی دوباره چک شوند — یک‌بار فیچر تأییدشده از بین رفته — و بار دوم هم: کپی IT Ops فاز ۱ کل Stage 2 (در دسترس بودن خودکار) را به نسخهٔ قبل برگرداند ولی migration `accounts/0005` را روی دیسک گذاشت، یعنی مدل و migration ناسازگار شدند. بعد از هر مرج اول `makemigrations --check` بزن.

## الهامات محصول / Backlog

اینها از یک تحقیق مقایسه‌ای روی ALICE/Actabl، Flexkeeping، Quore، Optii و Zendesk/Freshdesk درآمده‌اند. حالت آفلاین اپراتور و چندزبانگی پرتال مهمان از این فهرست پیاده شده‌اند (بخش‌های خودشان در همین فایل). باقی‌مانده پیاده نشده و تصمیم جداگانه می‌خواهد — بدون درخواست صریح سراغش نرو:

- **شفافیت هویت در چت** (اگر روزی Live Chat اضافه شد). در تست‌های کاربری هتل‌های ۵ ستاره، کاربرها گیج می‌شدند که با آدم حرف می‌زنند یا ربات. اگر چت اضافه شد، همیشه باید صریح بگوید «اپراتور [نام]» — نه یک حباب چت بی‌نام.

جمع‌بندی همان تحقیق: بیشتر چک‌لیست «ضروری» صنعت را داریم (SLA و معوق، بازخورد مهمان، داشبورد ادمین، تایم‌لاین، پیوست، آفلاین، دوزبانگی مهمان). از دریافت چندکاناله، QR کد اتاق و پیامک پیاده شده‌اند؛ اعلان لحظه‌ای (3.2) و تخصیص خودکار و SLA دومرحله‌ای (الهام از Odoo Helpdesk) هم پیاده شده‌اند؛ وب‌هوک PMS (3.3) و IPTV (3.4) مانده‌اند.

## QR کد اتاق

بدون هیچ زیرساخت جدید و بدون وابستگی npm تازه کار می‌کند: یک deep link که فیلد شماره اتاق را در **فرم لاگین** از پیش پر می‌کند.

```
https://<host>/guest/login?room=305
```

نکته‌ای که موقع پیاده‌سازی معلوم شد و ممکن است گمراه‌کننده باشد: **فرم ثبت درخواست اصلاً فیلد شماره اتاق ندارد.** اتاق سمت سرور از روی پروفایل مهمان تعیین می‌شود (`perform_create` در `apps/tickets/views.py` مقدار `room=guest_profile.room` را می‌گذارد) و `room_number` در سریالایزر فقط‌خواندنی است. پس گذاشتن `?room=` روی مسیر ثبت درخواست بی‌اثر است؛ تنها جایی که انسان شماره اتاق را تایپ می‌کند فرم لاگین است.

پارامتر فقط فیلد را **پیش‌پر** می‌کند و قفلش نمی‌کند، چون ممکن است مهمان QR اتاق اشتباهی را اسکن کند. از نظر امنیتی نگرانی خاصی ندارد: لاگین تطابق کد ملی با اتاق را اعتبارسنجی می‌کند و اتاق هم باید `OCCUPIED` باشد، پس یک QR دستکاری‌شده صرفاً به لاگین ناموفق می‌رسد.

تولید خود تصویر QR عمداً بیرون از اپ است — هتل با هر ابزار دلخواهی می‌سازدش. اضافه‌کردن کتابخانهٔ QR فقط برای یک صفحهٔ ادمین که در عمل یک‌بار استفاده می‌شود، هزینهٔ وابستگی‌اش را توجیه نمی‌کند.

## قبل از تحویل هر تغییر — Verification Gate

این روال به‌صورت اسکیل پروژه‌ای هم درآمده: `.claude/skills/deliver/SKILL.md`. با `/deliver` صدایش بزن تا همین ترتیب به‌علاوهٔ چک‌های مغایرت (migration جامانده، YAML قدیمی، هم‌راستایی ماشین‌حالت، عدد تست در اسناد) یک‌جا اجرا شود. خلاصه‌اش همین زیر است:

1. بک‌اند تغییر کرده؟ `python manage.py test` **کامل** روی PostgreSQL 16 واقعی — نه فقط اپ تغییریافته، نه SQLite.
2. فرانت‌اند تغییر کرده؟ هر سه باید سبز باشند: `npm run lint` ، `npm run build` ، `npm test`.
3. فقط فایل‌های تغییریافته/جدید را با جدول شماره‌گذاری‌شده (مسیر واقعی ← نام فایل تحویلی) تحویل بده، نه کل ریپو.
4. صبر کن Amirhossein روی مرورگر واقعی دستی تأیید کند، بعد سراغ Stage بعدی برو.

انتقال فایل بین دو ماشین ویندوز دستی انجام می‌شود و از اینجا `git push` زده نمی‌شود — این نسخه اصلاً `.git` ندارد.
