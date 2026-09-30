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
| تست بک‌اند | Django `TestCase`/`APITestCase` روی PostgreSQL واقعی — **۴۸۰ تست** |
| تست فرانت | Vitest + React Testing Library — **۱۴۵ تست** |
| Deployment | مستقیم روی هاست ویندوز، بدون Docker/Redis/Celery؛ کار زمان‌بندی‌شده با Windows Task Scheduler (`send_pending_sms` هر دقیقه، `pull_pms` هر چند دقیقه، `snapshot_room_stats` هر شب). هر جریان زندهٔ اپراتور یک thread سرور نگه می‌دارد — بخش «اعلان لحظه‌ای». `CHAT_TRANSPORT=websocket` (اختیاری، در استقرار) سرور را به ASGI + channel layer می‌برد — بخش «چت زنده» |

## دستورهای رایج

```bash
# بک‌اند (از ریشهٔ ریپو)
python manage.py migrate
python manage.py runserver localhost:8000      # localhost، نه 127.0.0.1 — بخش «دو تلهٔ همیشگی»
python manage.py seed_demo_data                # دادهٔ دموی فارسی: واحدها، دسته‌ها، اتاق، اپراتور، سرپرست، مهمان
python manage.py seed_demo_data --reset-passwords
python manage.py test                          # کل ۴۸۰ تست
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
  - `guests/` — Guest و لاگین مهمان، و `HotelInfo` (صفحهٔ راهنمای مهمان — بخش «قابلیت‌های Helpdesk»)
  - `rooms/` — Room و `RoomStatusLog` (لاگ append-only که خودِ `Room.save()` می‌نویسد)
  - `departments/` — CRUD ادمین
  - `tickets/` — هستهٔ پروژه: `Category`، `Ticket`، `TicketHistory`، `TicketNote`، `TicketAttachment`، `QuickRequestTemplate`، و `pdf.py`
  - `it_ops/` — عملیات داخلی واحد IT (`Process`، `Project`، `DepartmentRequest`، `Goal`، `Task`، `RoomDailyStat`) — بخش «IT Ops». **تنها اپی که ViewSet + Router دارد** نه generics؛ عمدی است (شش منبع CRUD هم‌شکل)
  - `notifications/` — صف پیامک مهمان (`SmsMessage`) و درایورهای ارسال — بخش «پیامک»؛ و جریان زندهٔ اپراتور و مهمان (`stream.py`) که پیام چت را هم حمل می‌کند — بخش‌های «اعلان لحظه‌ای» و «چت زنده»
  - `pms/` — اتصال به سیستم هتلداری هتل (هریس): وب‌هوک، دستور `pull_pms`، شبیه‌ساز و لاگ `PmsEvent` — بخش «اتصال به PMS»
  - `iptv/` — تلویزیون اتاق: صفحهٔ `/tv/<room>/` و API فقط‌خواندنی. **بدون مدل و بدون migration** — بخش «تلویزیون اتاق»
  - `extensions/` — فهرست داخلی‌های هتل، منتقل‌شده از پروژهٔ جدای `Hotel-extensions` — بخش «داخلی‌های هتل»
  - `chat/` — چت زنده مهمان↔اپراتور و اپراتور↔اپراتور؛ SSE امروز، وب‌سوکت آمادهٔ استقرار — بخش «چت زنده»
  - `news/` — اخبار و رویدادهای هتل برای مهمان و کارکنان، و روی تلویزیون اتاق — بخش «اخبار و رویدادها»
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
- **فرم «درخواست از IT» سه قابلیت سمت‌مهمانی دارد** (`/operator/it-requests`)، چون کار همان کار است از آن سر دیگر:
  - **قالب آماده:** `ITRequestTemplate` + `GET /it-ops/request-templates/` با `IsOperatorWithDepartment`. همان نقش `tickets.QuickRequestTemplate` را دارد ولی چیز دیگری پر می‌کند: عنوان، توضیح و **فوریت** (دسته اینجا وجود ندارد). فقط‌خواندنی روی API؛ مدیریتش Django Admin است.
  - **عکس:** `DepartmentRequestAttachment` و اکشن `POST …/outgoing-requests/{id}/attachments/`. **قاعدهٔ حجم از `apps.tickets.models.validate_attachment_size` import می‌شود، دوباره تعریف نشده** — یک `MAX_ATTACHMENT_SIZE_MB` برای کل پلتفرم. دسترسی از `get_queryset` ویوست می‌آید، پس واحد دیگر روی درخواست غیرخودش ۴۰۴ می‌گیرد نه ۴۰۳.
  - **بازخورد:** `rating` / `feedback` / `rated_at` روی `DepartmentRequest` و اکشن `POST …/{id}/rate/`. فقط `COMPLETED` و فقط یک‌بار؛ `REJECTED` نمره نمی‌گیرد (رد کردن گفت‌وگوست نه خدمتی که نمره بگیرد). شرطش در `DepartmentRequest.can_be_rated` است و سریالایزر همان را به فرانت می‌دهد، تا پنل و endpoint دربارهٔ «کی جعبهٔ بازخورد را نشان بده» اختلاف پیدا نکنند. سمت IT این سه فیلد **فقط‌خواندنی‌اند** — `test_it_cannot_rate_its_own_work_through_the_it_endpoints` این را pin می‌کند.
- **ستاره‌ها مشترک‌اند:** `components/star-rating.tsx` (با `useOptionalLocale`) هم برای امتیاز مهمان و هم برای بازخورد واحد. نسخهٔ محلی داخل صفحهٔ تیکت مهمان حذف شد.
- **فرم‌های صفحهٔ IT** (`components/it-ops/item-dialog.tsx` + `resource-panel.tsx`) یک دیالوگ مشترک‌اند که با field spec کار می‌کنند. دو قاعده که شکستنشان ۴۰۳ می‌سازد: در ویرایش **فقط فیلدهای تغییرکرده** فرستاده می‌شوند (`changedFields`) — چون `CanWorkOnITItem` صرفِ حضور یک فیلد سرپرستی در بدنه را رد می‌کند، حتی با مقدار دست‌نخورده؛ و فیلدهایی که بیننده اجازه‌شان را ندارد اصلاً نمایش داده نمی‌شوند (`isItFieldEditable`). در ساخت، فیلد خالی فرستاده نمی‌شود تا پیش‌فرض سرور اعمال شود.
- `DepartmentRequestSerializer` در schema با نام `ITDepartmentRequest` است، چون `DepartmentSerializer` با `COMPONENT_SPLIT_REQUEST` خودش کامپوننتی به نام `DepartmentRequest` می‌سازد. **دکوراتور `@extend_schema_serializer` باید بچسبیده به همان کلاس بماند** — یک‌بار موقع اضافه‌کردن سریالایزرهای تازه بینشان کلاس افتاد و دکوراتور روی کلاس اشتباه نشست؛ نشانه‌اش هشدار «2 components with identical names» در `spectacular` است. enumهای وضعیت/اولویت IT هم در `ENUM_NAME_OVERRIDES` نام گرفته‌اند؛ اگر enum تازه‌ای با نام تکراری اضافه شد، spectacular اسم هش‌دار می‌سازد — همان‌جا نامش بده.

## قابلیت‌های Helpdesk (الهام از Odoo)

چهار قابلیت از بررسی ماژول Helpdesk در Odoo. هر کدام از Django Admin مدیریت می‌شود.

- **قالب پیامک برای هر وضعیت** — `notifications.MessageTemplate`، یک ردیف برای هر رویداد (ثبت، شروع کار، حل، لغو). متن با متغیرهای `{title} {ticket_id} {department} {room} {hotel}`؛ متغیر ناشناخته در `clean()` رد می‌شود تا غلط تایپی به مهمان نرسد. `is_active=False` یعنی برای آن رویداد پیامکی نمی‌رود؛ بدون ردیف ← متن پیش‌فرض `services.DEFAULT_BODIES`. migration `notifications/0003` متن‌های پیش‌فرض را به‌صورت قالب قابل‌ویرایش گذاشت (کپی متن، نه import از کد). پیامک «شروع کار» **فقط بار اول** می‌رود (`first_response_at` قبلاً خالی بوده)، نه در هر رفت‌وبرگشت OPEN↔IN_PROGRESS.
- **گزارش امتیاز مهمان** — `_ratings` در `services.py`: میانگین، تعداد، توزیع ۱ تا ۵ و ۵ نظر متنی آخر؛ به‌علاوهٔ `rating_avg`/`rating_count` در هر ردیف «به تفکیک واحد» (ادمین) و «بار کاری اپراتورها» (واحد). پنجرهٔ زمانی بر اساس `resolved_at` است (فیلد جدای «زمان امتیاز» نداریم). میانگینِ بی‌امتیاز `null` است نه صفر.
- **پاسخ‌های آماده** — `tickets.CannedResponse` (واحد خالی = برای همهٔ واحدها)، `GET /operator/canned-responses/`. فرانت: `components/canned-response-picker.tsx` کنار یادداشت، نتیجهٔ رسیدگی و دیالوگ Resolve؛ متن را به انتهای فیلد اضافه می‌کند، جایگزین نمی‌کند.
- **ادغام تیکت تکراری** — `services.merge_tickets` و `POST /operator/tickets/{id}/merge/` (فقط سرپرست). قواعد: همان مهمان و همان واحد (دو مهمان که هر دو حوله خواسته‌اند دو درخواست‌اند)، تکراری هنوز OPEN، مقصد هنوز باز. اثر: تکراری CANCELLED با `merged_into`، عکس‌هایش به مقصد می‌روند، یادداشت داخلی با توضیحش روی مقصد، رویداد `MERGED` در هر دو تایم‌لاین، و **پیامک لغو نمی‌رود** (درخواست مهمان هنوز در حال رسیدگی است). `merge-candidates/` تیکت‌های باز دیگر همان مهمان را می‌دهد. مهمان روی تیکت ادغام‌شده پیوند به تیکت اصلی می‌بیند.
- **صفحهٔ راهنمای مهمان** — `guests.HotelInfo` (دوزبانه: `title_en`/`body_en` اختیاری با برگشت به فارسی)، `GET /guest/hotel-info/` **فقط برای مهمانِ واردشده** (رمز وای‌فای عمومی نیست)، صفحهٔ `/guest/info` با پیوند از داشبورد و فرم ثبت درخواست.

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

## چت زنده (Stage 4.1)

`apps/chat` — پشتیبانی لحظه‌ای؛ هم مهمان↔اپراتور و هم اپراتور↔اپراتور (تصمیم کاربر: «هر دو»).

- **یک جدول برای هر دو نوع گفت‌وگو:** `Conversation.kind` یا `GUEST` است یا `STAFF`. پیام، شمارش نخوانده و تحویل زنده در هر دو یکی است؛ دو جدول یعنی نوشتن همهٔ اینها دو بار، و تفاوت واقعی‌شان فقط یک فیلد است.
- **`services.visible_conversations(user)` تنها قاعدهٔ دسترسی است** و هر سه سطح از آن می‌خوانند: endpointهای REST، جریان SSE و کانسیومر وب‌سوکت. سه نسخه از این قاعده دیر یا زود سه قاعدهٔ متفاوت می‌شد و آنکه دررفته بود همان‌جایی بود که گفت‌وگوی یک مهمان را به دیگری نشان می‌داد. مهمان فقط نخ‌های خودش، اپراتور نخ‌های مهمانان **واحد خودش** (همان scoping تیکت) به‌علاوهٔ نخ‌های کارکنانی که در آن‌هاست، ادمین فقط نخ‌های کارکنانی که در آن‌هاست — **پشتیبانی مهمان مال واحدهاست نه مدیریت**.
- **گفت‌وگوی مهمان با هر واحد یکی است** و در طول اقامت دوباره استفاده می‌شود (`guest_conversation`): مهمانی که دو چیز از خانه‌داری خواسته یک گفت‌وگو دارد، وگرنه اپراتور در پنجره‌ای جواب می‌دهد که مهمان بسته است. گفت‌وگوی بستهٔ قبلی دوباره باز نمی‌شود.
- **نخ کارکنان بی‌موضوع تکرار نمی‌شود** (`find_staff_conversation`): «پیام به رضا» دو بار، دو گفت‌وگوی خالی نمی‌سازد. با موضوع، همیشه نخ تازه.
- **شمارش نخوانده دو برش زمانی دارد و عمداً دو مقایسهٔ متفاوت:** `last_read_at` با `>` (آن لحظه خوانده شده) و `joined_at` با `>=` (از لحظهٔ افزوده‌شدن، همه‌چیز مال شماست). همین `>=` است که روی ویندوز — با تیک ~۱۵ میلی‌ثانیه‌ای ساعت — پیامی که بلافاصله بعد از پیوستن نوشته شده را گم نمی‌کند. تست `test_a_message_arriving_in_the_same_clock_tick_as_the_join_still_counts` نگهبانش است.
- **هویت فرستنده صریح است — همان بند Backlog:** `sender_label` همیشه «اپراتور رضا» / «مهمان سارا احمدی» / «سیستم» است، هرگز حباب بی‌نام. نام مهمان از `Guest.full_name` می‌آید نه username حساب، وگرنه «مهمان guest_0011122233» نمایش داده می‌شد. `message_payload()` تنها شکل روی سیم است و REST و SSE و وب‌سوکت هر سه همان را می‌فرستند.
- **ترابرد یک تنظیم است، نه معماری** (`delivery.py` + `CHAT_TRANSPORT`):
  - `sse` (پیش‌فرض) — چیزی push نمی‌شود؛ همان جریان Stage 3.2 رویداد `chat.message` را هم با cursor حمل می‌کند. روی همین سرور WSGI، بدون Redis و بدون ASGI. **چت جریان دوم باز نمی‌کند**: هر جریان باز یک thread سرور می‌گیرد و دادن دو جریان به هر اپراتور هزینهٔ باز بودن پنل را دو برابر می‌کرد.
  - `websocket` — **نوشته و تست شده ولی خاموش تا استقرار** (تصمیم کاربر). `consumers.py` بالای فایل چهار کار لازم برای روشن‌کردنش را فهرست کرده. `publish()` هرگز raise نمی‌کند: ردیف در دیتابیس است و جریان backstop است، پس push ناموفق حداکثر `SSE_POLL_SECONDS` تأخیر است نه پیام گم‌شده.
  - **فرانت هم برای یکی ساخته نشده:** `GET /chat/config/` می‌گوید کدام زنده است و `lib/chat.ts` بر اساسش تصمیم می‌گیرد. پس عوض‌کردن ترابرد یک تنظیم سرور است نه انتشار تازهٔ فرانت.
- **بلیت وب‌سوکت (`tickets.py`):** دست‌دادن وب‌سوکت هدر Authorization نمی‌فرستد و بر اساس بخش امنیت، توکن نباید در URL برود. پس پنل با یک درخواست معمولیِ احراز‌شده بلیت می‌گیرد: تصادفی، `CHAT_TICKET_SECONDS` (پیش‌فرض ۳۰) عمر، و **یک‌بارمصرف** (redeem حذفش می‌کند). در کش نگه داشته می‌شود نه جدول — چند ثانیه عمر دارد و جدول جاروکشی می‌خواست. هر تلاش اتصال بلیت تازه می‌گیرد، تا reconnect نتواند بلیت قبلی را دوباره بفرستد.
- **کانسیومر همان `visible_conversations` و همان `post_message` را صدا می‌زند** — پس سوکت نمی‌تواند به نخی برسد که REST ردش می‌کند، و دو مسیر نمی‌توانند دربارهٔ آنچه ذخیره می‌شود اختلاف پیدا کنند. بی‌بلیت ۴۴۰۱، نخ غیرخودی ۴۴۰۳.
- **ارسال همیشه با REST است، حتی روی وب‌سوکت:** نوشتن باید تأیید شود و `socket.send` بی‌جواب است. سوکت راهی است که **طرف دیگر** خبردار می‌شود، نه راهی که پیام ذخیره می‌شود.
- **جریان مهمان:** `GET /api/v1/guest/events/` (`guest_event_stream`) فقط چت را حمل می‌کند — مهمان چیز دیگری برای شنیدن لحظه‌ای ندارد و دادن جریان اپراتور به او تیکت‌های واحد را لو می‌داد. از layout پرتال اجرا می‌شود نه از صفحهٔ چت، تا پاسخ به مهمانی که رفته فهرست درخواست‌هایش هم برسد.
- **فرانت:** `components/chat/chat-thread.tsx` بین پرتال مهمان و پنل **مشترک** است (همان نخ از دو سر؛ نسخهٔ دوم جایی بود که دو طرف دربارهٔ «چه کسی چه نوشت» دررو می‌کردند)، با `useOptionalLocale`. رسیدن پیام هرچه ترابردش باشد به یک رویداد پنجره می‌رسد: `CHAT_EVENT`. صفحه‌ها با `key={conversationId}` کامپوننت را remount می‌کنند نه اینکه state را در effect صفر کنند — قاعدهٔ `react-hooks/set-state-in-effect`.
- بستن گفت‌وگو کار Django Admin است؛ در نخ بسته هیچ‌کس نمی‌نویسد (۴۰۰).

## اخبار و رویدادها (Stage 4.2)

`apps/news` — یک `NewsItem`، دو مخاطب. مدیریتش **فقط Django Admin** است و API فقط‌خواندنی، دقیقاً مثل اتاق و واحد و راهنمای هتل و فهرست داخلی‌ها.

- **پنجرهٔ انتشار تنها چیزی است که تصمیم می‌گیرد چه روی صفحه است** (`NewsItemQuerySet.published`): فعال، `publish_at` گذشته، `expires_at` نرسیده یا خالی. پس کسی لازم نیست صبح بعدِ رویداد یادش باشد اطلاعیه را بردارد. اکشن «Take down now» در ادمین `expires_at` را می‌گذارد، **حذف نمی‌کند** — اطلاعیه در سابقه می‌ماند.
- **دو endpoint، هرکدام یک scope ثابت** — همان شکل خلاصهٔ آمار و به همان دلیل: `GET /guest/news/` با `IsGuest` و `GET /operator/news/` با `IsStaffReadAdminWrite`. **عمداً `IsAdminRole` نیست** (خواندن را برای هر کاربر واردشده باز می‌گذارد و مهمان هم کاربر واردشده است) و **عمداً `IsOperator` هم نیست** (ادمین هم کاربر پنل است و بریفینگ شیفت مال او هم هست).
- `audience` سه حالت دارد: `GUEST` / `STAFF` / `BOTH`. آیتم کارکنانِ دارای `department` فقط برای همان واحد؛ بی‌واحد برای کل هتل. ادمین واحد ندارد، پس آیتم‌های کل هتل را می‌بیند نه آیتم واحدها.
- **دوزبانه مثل بقیهٔ پرتال مهمان** (`title_en`/`body_en` اختیاری با برگشت به فارسی). آیتم کارکنان نیازی ندارد — پنل عمداً فارسی است.
- **روی تلویزیون اتاق هم می‌رود** و از همان `services.guest_news()` — پس رویداد امشب نمی‌تواند در پرتال باشد و روی تلویزیون نباشد، یا بعد از بسته‌شدن پنجره روی یکی بماند. فقط مخاطب `GUEST`؛ `test_the_page_renders_for_a_television_on_the_iptv_network` هم حضور خبر مهمان و هم **نبودن** بریفینگ کارکنان را pin می‌کند.
- `event_at` جدا از پنجرهٔ انتشار است: یکی «رویداد کِی است» و دیگری «اطلاعیه کِی روی صفحه است».
- فرانت: `components/news-list.tsx` بین پرتال و پنل مشترک است — تفاوت دو مخاطب این است که کدام endpoint فهرست را پر کرده، نه اینکه اطلاعیه چه شکلی است.

## اعلان دسکتاپ ویندوز (Stage 4.3)

`frontend/src/lib/desktop-notify.ts` — با Notification API خودِ مرورگر؛ **نه چیزی نصب می‌شود نه helper بومی**. روی ویندوز، اعلان یک تب باز Chrome یا Edge در Action Center می‌نشیند و toast می‌زند، که همان خواسته است: اپراتور لازم نیست به پنل نگاه کند.

- **سه چیزی که باید صریح باشد، چون هر سه روی شبکهٔ هتل پیش می‌آید و شکست بی‌صدا شبیه فیچر خراب است:**
  1. **secure context لازم است** — https یا localhost. پنل روی http از یک ماشین شبکهٔ هتل کلاً `Notification` ندارد. `support()` می‌گوید کدام‌یک از سه دلیل است و دکمهٔ هدر **غیرفعال با tooltip توضیح** می‌شود، نه سوئیچی که کاری نمی‌کند.
  2. **اجازه باید از یک کلیک واقعی خواسته شود** — مرورگرها prompt هنگام بارگذاری صفحه را نادیده می‌گیرند (کروم برای همیشه رد می‌کند). پس هیچ‌جا خودکار پرسیده نمی‌شود.
  3. **«granted» همیشگی نیست** — کاربر می‌تواند در مرورگر پسش بگیرد، پس هر اعلان دوباره چک می‌کند نه اینکه به یک فلگ اعتماد کند.
- سوئیچ خودِ اپراتور در `localStorage` هر مرورگر است و **پیش‌فرض خاموش**؛ خواندن و نوشتنش در try/catch، چون پنجرهٔ ناشناس و site data بسته همان‌جا می‌افتند.
- **اعلان عمداً `silent: true` است** — صدا کار `lib/chime.ts` است و دو صدا با هم از هرکدام بدتر است.
- `tag` دارد (`ticket-<id>`، `chat-<conversation>`)، پس بیست درخواست تازه جای هم را می‌گیرند نه اینکه دسکتاپ را دفن کنند.
- وصل به همان سه رویداد جریان زنده: تیکت تازه، تیکتی که به من سپرده شد، پیام چت تازه (وقتی روی صفحهٔ چت نیستم).

## داخلی‌های هتل (ادغام پروژهٔ Hotel-extensions)

`apps/extensions` — فهرست شماره‌های داخلی. پیش‌تر یک پروژهٔ جدا بود (مخزن `Hotel-extensions`: فلسک + SQLAlchemy روی SQLite + قالب Jinja) و به تصمیم کاربر به داخل پلتفرم منتقل شد، نه اینکه دو اپ کنار هم در یک مخزن بمانند. مدل داده همان مدل فلسک است، با دو تفاوت که تازه اینجا ممکن شد:

- **واحد، ردیف واقعی `departments.Department` است** نه فهرست متنی جدا — همان تصمیمی که در IT Ops گرفته شد. `Department.working_hours` (متن آزاد) از همان نسخه آمد، چون زیر هر شماره نمایش داده می‌شود.
- **کاربر و ورود و مسیر مخفی ادمین و idle timeout نسخهٔ فلسک حذف شدند**؛ دسترسی از نقش‌های خود پلتفرم می‌آید.

- **`IsStaffReadAdminWrite` در `apps/core/permissions.py`:** اپراتور و مدیر می‌خوانند، فقط مدیر می‌نویسد. **عمداً `IsAdminRole` نیست** — آن خواندن را برای «هر کاربر واردشده» باز می‌گذارد و مهمان هم کاربر واردشده است؛ این فهرست نام و موبایل و محل کارکنان را دارد. در نسخهٔ فلسک این صفحه عمومی بود؛ اینجا نیست. `test_a_guest_cannot_read_the_staff_directory` این را pin می‌کند — اگر روزی خواستی برای مهمان باز شود، تصمیم هتل است و آن تست اول قرمز می‌شود.
- **صفحهٔ پنل فقط‌خواندنی است** (`/operator/extensions`)؛ مدیریت در Django Admin انجام می‌شود، دقیقاً مثل اتاق و واحد و دسته. برای همین اینجا دیالوگ ساخت/ویرایش نداریم.
- **یک FilterSet برای لیست و هر دو خروجی** (`filters.py`)، به همان دلیلی که نسخهٔ فلسک `build_filtered_query` را مشترک کرده بود: «خروجی» باید همان چیزی باشد که روی صفحه است. تست فرانت هم پین می‌کند که دانلود با همان پارامترهای لیست صدا زده می‌شود.
- **حذف بازگشت‌پذیر:** `DELETE` فقط `is_deleted` را می‌گذارد و اکشن‌های Django Admin برمی‌گردانند یا قطعی حذف می‌کنند. queryset همهٔ ویوها `Extension.objects.alive()` است — ویوی جدید را هم از همان بساز، وگرنه ردیف‌های سبد دوباره ظاهر می‌شوند.
- **ایمپورت در `services.import_rows`** با `commit=False` که همان «پیش‌نمایش» فلسک است: گزارش می‌دهد و `transaction.set_rollback(True)` می‌زند، پس مسیر کد یکی است و دو نسخهٔ واگرا نمی‌شود. دستور `import_extensions` بدون `--confirm` چیزی نمی‌نویسد. upsert روی شمارهٔ داخلی، ارقام فارسی به ASCII (`ascii_digits`)، و واحد ناموجود ساخته می‌شود (کد یکتا از `slugify` نام).
- **ستون‌های فایل عمداً همان ستون‌های فلسک‌اند** (`exports.COLUMNS`) تا فایل اکسل موجود هتل بدون دست‌خوردن وارد شود و خروجی دوباره قابل ورود باشد. `status` کلمهٔ فارسی است نه بولین؛ `INACTIVE_VALUES` همان قاعدهٔ قبلی را نگه می‌دارد.
- **PDF:** طرح دو ستونه و بلوک‌های ادغام‌شدهٔ نسخهٔ فلسک حفظ شده (برای کم‌کردن کاغذ)، ولی با platypus و فونت وزیرمتن. **پلامبینگ فارسی PDF مشترک شد:** `register_fonts()`، `shape()` و نام‌های `FONT_*` در `apps/tickets/pdf.py` از حالت private درآمدند و `apps/extensions/pdf.py` همان‌ها را import می‌کند — یک پیاده‌سازی shaping، نه دو تا. (قواعد فونت و wrap در بخش «خروجی PDF تیکت» همان‌جا سر جایش است.)
- **وابستگی تازه: `openpyxl`** — تنها راه خواندن و نوشتن xlsx؛ در `requirements/base.txt` اضافه شد. CSV با کتابخانهٔ استاندارد است و با `utf-8-sig` نوشته می‌شود، وگرنه اکسل ویندوز فارسی را خراب نشان می‌دهد.
- **راحتی‌های سمت مرورگر، همان‌طور که در فلسک بودند:** ستاره‌کردن شماره‌ها و فیلتر «فقط علاقه‌مندی‌ها»، دکمهٔ کپی، پنجرهٔ جزئیات، و نمای جدول/کارت. ستاره‌ها و نمای انتخابی در `localStorage` هر مرورگر می‌مانند (`extensions-favourites` و `extensions-view`) و **هرگز سمت سرور نمی‌روند** — سلیقهٔ یک نفر است نه دادهٔ هتل. خواندن و نوشتنشان در try/catch است، چون پنجرهٔ ناشناس و site data بسته هر دو همان‌جا می‌افتند.
- **به‌روزرسانی خودکار با یک نشانگر، نه با کشیدن دوبارهٔ فهرست:** `GET /extensions/version/` رشتهٔ «تعداد:بیشترین id:آخرین updated_at» می‌دهد و صفحه هر ۳۰ ثانیه فقط همین را می‌پرسد؛ عوض شد، آن‌وقت لیست را دوباره می‌خواند. همان کاری که نسخهٔ فلسک با `/api/version` می‌کرد. ویرایش یک ردیف هم تکانش می‌دهد (چون `updated_at` در آن هست)، نه فقط اضافه/حذف.
- **`ExtensionActivity` تاریخچه است، نه جدول کاری:** از سه مسیری که واقعاً چیزی را عوض می‌کنند نوشته می‌شود (ویوهای API، Django Admin، ایمپورت) و **عمداً از signal نه** — signal ردیف را می‌بیند ولی آدم را نه، و کل ارزش این لاگ همان «چه کسی» است. `actor` متن است نه FK، تا حذف کاربر تاریخچه را نبرد. ایمپورت **یک خط** می‌نویسد نه یکی به ازای هر ردیف، وگرنه بارگذاری فهرست هتل کل لاگ را دفن می‌کند؛ و پیش‌نمایش (`commit=False`) هیچ خطی نمی‌نویسد.
- **بکاپ خروجی اکسل است، نه دامپ دیتابیس:** `services.backup_extensions` کل فهرست — با ردیف‌های سبد — را با تاریخ در نام فایل در `EXTENSIONS_BACKUP_DIR` می‌نویسد. ستون‌هایش همان ستون‌های ایمپورت‌اند، پس بکاپ **قابل بازگرداندن** است. نسخهٔ فلسک فایل SQLite خودش را می‌داد؛ اینجا دیتابیس مال کل پلتفرم است و بکاپ‌گیری از آن کار استقرار است نه یک دکمه در یک صفحه. دستور `backup_extensions` هم هست تا در Task Scheduler شبانه اجرا شود.
- **فرم ایمپورت در Django Admin** (`admin/extensions/import.html` + `get_urls`): آپلود ← پیش‌نمایش ← تأیید. ردیف‌های پارس‌شده بین دو مرحله در **session** می‌مانند نه فایل موقت (نسخهٔ فلسک با توکن و پوشهٔ tmp این کار را می‌کرد و باید تمیزکاری می‌کرد). پیش‌نمایش همان `import_rows(commit=False)` است، پس نمی‌تواند چیزی را وعده دهد که تأیید جور دیگری انجام دهد.
- **`read_rows` حتماً باید `workbook.close()` بزند.** openpyxl با `read_only=True` فایل را باز نگه می‌دارد و روی ویندوز تا بسته نشود نه پاک می‌شود نه جابه‌جا — `WinError 32`. هم فایل موقتِ آپلود ادمین و هم رفت‌وبرگشت بکاپ به همین گیر کردند؛ تست `test_trashed_numbers_are_in_the_backup_too` نگهبانش است.
- `seed_demo_data` هشت داخلی نمونه و ساعت کاری واحدها را هم می‌سازد.

**مخزن قدیمی:** `Hotel-extensions` بازنشسته می‌شود. یک نکتهٔ امنیتی آن‌جا: فایل `.secret_key` در `.gitignore` هست ولی از قبل tracked بوده و در مخزن عمومی مانده — کلید امضای session فلسک عمومی است. اگر آن اپ هنوز جایی بالاست: `git rm --cached .secret_key`، بعد کلید را دور بیندازید.

## تلویزیون اتاق (Stage 3.4)

`apps/iptv` — مهمان درخواست‌های بازش و راهنمای هتل را روی تلویزیون اتاق می‌بیند. **فقط‌خواندنی؛ تصمیم کاربر بود:** با ریموت نه ثبت درخواست و نه امتیازدهی. اپ مدل ندارد (هیچ داده‌ای از خودش نگه نمی‌دارد) — پس migration هم ندارد.

- **دو سطح، یک پاسخ:** `services.room_screen()` تنها منبع است و هر دو مسیر از آن می‌خوانند — API (`GET /api/v1/iptv/rooms/<room>/`) برای سیستمی که منوی خودش را دارد، و صفحهٔ `GET /tv/<room>/` برای سیستمی که فقط یک URL باز می‌کند. کاربر گفت نمی‌داند شرکت IPTV کدام را پشتیبانی می‌کند، پس هر دو ساخته شد.
- **صفحهٔ تلویزیون عمداً ابتدایی است:** HTML سمت سرور، بدون جاوااسکریپت، بدون فونت وب، به‌روزرسانی با `<meta http-equiv="refresh">`. ست‌تاپ‌باکس هتل مرورگر قدیمی دارد و صفحه‌ای که بالا نیاید از صفحهٔ ساده بدتر است. اندازه‌ها `vh`/`vw`اند و حاشیه برای overscan تلویزیون باز گذاشته شده. **به build فرانت‌اند وابسته نیست** — رنگ‌ها از `globals.css` کپی شده‌اند، نه import.
- **احراز هویت در `auth.py`، نه JWT** — پشت تلویزیون آدمی نیست، فقط یک اتاق: API با `X-IPTV-Key`؛ صفحه با `IPTV_ALLOWED_NETWORKS` (CIDR) و/یا امضای `?t=` از `IPTV_PAGE_SECRET`. **هیچ‌کدام تنظیم نشده ← هر دو بسته**، همان قاعدهٔ وب‌هوک PMS. هر دو تنظیم شده ← هر دو باید پاس شوند.
- **`X-Forwarded-For` عمداً باور نمی‌شود** (هرکسی می‌تواند بفرستدش و allowlist را تزئینی کند)؛ فقط `REMOTE_ADDR`. پشت nginx باید `real_ip` تنظیم شود — در README نوشته شده. تست `test_a_forwarded_for_header_cannot_fake_the_network` این را pin می‌کند.
- **اتاق خالی، اتاق ناشناس و اتاق بی‌درخواست پاسخ یکسان می‌دهند** (۲۰۰ با `has_active_stay: false`)، نه ۴۰۴ — وگرنه همین صفحه می‌گوید کدام اتاق‌ها فروخته شده‌اند. تست `test_an_empty_room_and_an_unknown_room_answer_the_same`.
- **هیچ دادهٔ شخصی روی تلویزیون نمی‌رود:** نه کد ملی، نه تلفن، نه نام مهمان، نه نام اپراتور. `test_the_screen_carries_no_personal_data` این را pin می‌کند؛ اگر روزی خواستی خوشامد با نام مهمان اضافه کنی، آن تست اول قرمز می‌شود — تصمیمش با هتل است، بی‌صدا عوضش نکن.
- **خروج مهمان کار اضافه‌ای لازم ندارد:** `current_guest()` مثل لاگین مهمان `room__status=OCCUPIED` می‌خواهد، و PMS با check-out اتاق را آزاد و `room` را خالی می‌کند — پس تلویزیون خودبه‌خود پاک می‌شود.
- **برچسب وضعیت از `apps/tickets/labels.py`** می‌آید؛ همان جایی که `pdf.py` هم از آن می‌خواند (قبلاً داخل `pdf.py` بود و منتقل شد). سه سطح سمت سرور نباید سه کلمهٔ متفاوت برای یک وضعیت بگویند. نسخهٔ فرانت همچنان `lib/ticket-labels.ts` است.
- `manage.py iptv_urls --base-url https://…` فهرست «یک URL برای هر اتاق» را می‌دهد که به شرکت IPTV تحویل می‌شود (`--csv` هم دارد) و اگر امضا تنظیم نشده باشد هشدار می‌دهد.

## اتصال به PMS (Stage 3.3)

`apps/pms` — ورود/خروج/جابه‌جایی مهمان از سیستم هتلداری هتل (**هریس**، شرکت هریس) به این سامانه می‌آید. هریس API عمومی مستند ندارد (دسترسی را به شرکای یکپارچه‌سازی می‌دهد)، پس این اپ **آداپتورمحور** نوشته شده: چیزی که از هریس لازم است سه قلم است (آدرس سرویس «چه چیزی از فلان زمان عوض شده»، یک اعتبارنامه، و یک نمونهٔ واقعی از هر رویداد) و بقیه‌اش تنظیمات است.

- **تصمیم کاربر: کشیدن، نه فرستادن.** `manage.py pull_pms` (Task Scheduler، هر چند دقیقه) از PMS می‌پرسد؛ نشانگر در `PmsSyncState` (تک‌ردیفی، `load()`). وب‌هوک `POST /api/v1/pms/events/` هم هست برای وقتی هریس بتواند خودش خبر بدهد — **هر دو به `services.apply_event` می‌رسند**، منطق یکی است.
- **`apply_event` هرگز raise نمی‌کند.** هر تماس یک ردیف `PmsEvent` می‌شود با بدنهٔ خام و نتیجه: `PROCESSED` / `FAILED` / `IGNORED` (تکراری) / `REJECTED` (نوع ناشناخته). وب‌هوک بعد از احراز هویت همیشه ۲۰۰ می‌دهد — سیستمی که ما کنترلش نمی‌کنیم نباید به‌خاطر دادهٔ بد خودش در حلقهٔ retry بیفتد، و ردیف ناموفق از Django Admin دوباره اجرا می‌شود.
- **بی‌تکرار بودن با `external_id` یکتا:** شناسهٔ خود PMS، و اگر نفرستاد sha256 بدنه. تحویل دوباره ثبت می‌شود ولی اعمال نمی‌شود.
- **نگاشت فیلدها تنظیمات است نه کد:** `DEFAULT_FIELD_MAP` (مسیر نقطه‌ای در JSON آن‌ها) و `DEFAULT_EVENT_MAP`، قابل override با `PMS_FIELD_MAP` / `PMS_EVENT_MAP`. وقتی نمونهٔ واقعی هریس رسید، اول این دو را عوض کن — نه هندلرها را.
- **کلاینت‌ها در `client.py`:** پیش‌فرض `FilePmsClient` (رویدادها از یک فایل JSON) تا کل مسیر پیش از دسترسی واقعی قابل تست و دمو باشد؛ `HarrisPmsClient` با urllib و بدون وابستگی تازه. PMS قطع ← `PmsUnavailable` که `pull_pms` به‌شکل هشدار ثبت می‌کند، نه crash.
- **احراز هویت وب‌هوک در `auth.py`** (نه JWT): `X-PMS-Key` با مقایسهٔ constant-time، و امضای اختیاری `X-PMS-Signature`. **`PMS_SHARED_KEY` خالی یعنی همه رد می‌شوند** — یکپارچه‌سازی تنظیم‌نشده نباید باز بماند. `PMS_HMAC_SECRET` که مقدار بگیرد، امضا الزامی می‌شود (نه اختیاری) تا روشن‌کردنش فراموش نشود.
- **خروج مهمان (تصمیم کاربر):** `guest.room = None` + `checked_out_at`، اتاق آزاد می‌شود مگر `MAINTENANCE` باشد، و تیکت‌های باز **بسته نمی‌شوند** — فقط یادداشت داخلی می‌گیرند (`_note_open_tickets`). همین خالی‌شدن اتاق دسترسی مهمان را هم تمام می‌کند، چون لاگین مهمان تطابق اتاق و `OCCUPIED` بودنش را می‌خواهد؛ تا اسکان دوباره نمی‌تواند وارد شود.
- **PMS مرجع فهرست اتاق‌هاست:** اتاق ناشناخته ساخته می‌شود، نه اینکه رویداد دور ریخته شود (`_room`).
- **`purge_departed_guests` عمداً به هیچ‌چیز وصل نیست.** تصمیم کاربر: «کد آماده باشد ولی فعلاً پاک نشود». بدون `--confirm` فقط گزارش می‌دهد، در Task Scheduler گذاشته نشده، و مشخصات را بی‌نام می‌کند (`erased-<pk>`) به‌جای حذف ردیف — تیکت‌ها و آمار حفظ می‌شوند.
- `simulate_pms` جای هریس را برای تست دستی می‌گیرد و رویداد را با `source=SIMULATOR` ثبت می‌کند؛ رویداد ناموفق `CommandError` می‌دهد تا در اسکریپت بی‌صدا رد نشود.

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
- **`os error 32` در build/dev ویندوز** («used by another process» روی یک فایل سورس): کد ایرادی ندارد؛ فایل لحظه‌ای قفل بوده — معمولاً کپی فایل‌ها وسط `npm run dev`، دو `next dev` هم‌زمان، آنتی‌ویروس یا OneDrive. سرور dev را ببند، پروسه‌های node جامانده را ببند، `.next` را پاک کن، دوباره بالا بیاور؛ و فایل‌ها را همیشه با سرور خاموش کپی کن.
- **کش `.next`:** بعد از تغییر ساختاری، اگر خطای عجیب TypeScript روی `routes.d.ts` دیدی، `.next` را کامل پاک کن.
- **تست زمان‌محور روی ویندوز:** ساعت ویندوز حدود هر ۱۵ میلی‌ثانیه تیک می‌خورد، پس `since = timezone.now()` و `created_at` ردیفی که بلافاصله بعدش ساخته می‌شود می‌توانند دقیقاً برابر باشند و شرط `>` فیل شود. در تست یک فاصلهٔ صریح بگذار (`- timedelta(seconds=1)`)؛ `test_new_count_reflects_tickets_created_after_since` یک‌بار دقیقاً همین‌طور فلیکی بود.
- **`swagger_fake_view`:** هر `get_queryset` که از `request.user` فیلتر می‌گیرد باید اول `getattr(self, "swagger_fake_view", False)` را چک کند و `.none()` برگرداند؛ وگرنه `spectacular` با AnonymousUser می‌شکند و هشدار می‌دهد (نمونه: `OutgoingITRequestViewSet`).
- **مرج دستی:** وقتی Amirhossein خودش یک Stage را پیاده می‌کند، فیچرهای تأییدشدهٔ قبلی دوباره چک شوند — یک‌بار فیچر تأییدشده از بین رفته — و بار دوم هم: کپی IT Ops فاز ۱ کل Stage 2 (در دسترس بودن خودکار) را به نسخهٔ قبل برگرداند ولی migration `accounts/0005` را روی دیسک گذاشت، یعنی مدل و migration ناسازگار شدند. بعد از هر مرج اول `makemigrations --check` بزن.

## الهامات محصول / Backlog

اینها از یک تحقیق مقایسه‌ای روی ALICE/Actabl، Flexkeeping، Quore، Optii و Zendesk/Freshdesk درآمده‌اند. حالت آفلاین اپراتور و چندزبانگی پرتال مهمان از این فهرست پیاده شده‌اند (بخش‌های خودشان در همین فایل). باقی‌مانده پیاده نشده و تصمیم جداگانه می‌خواهد — بدون درخواست صریح سراغش نرو:

- **شفافیت هویت در چت — پیاده شد.** در تست‌های کاربری هتل‌های ۵ ستاره، کاربرها گیج می‌شدند که با آدم حرف می‌زنند یا ربات. چت (Stage 4.1) همیشه صریح می‌گوید «اپراتور رضا» و نه حباب بی‌نام؛ `sender_label` در `apps/chat/serializers.py` و تست‌های `SenderIdentityTests`. اگر روزی پاسخ خودکار اضافه شد، همان قاعده باید برایش هم برقرار بماند.

جمع‌بندی همان تحقیق: بیشتر چک‌لیست «ضروری» صنعت را داریم (SLA و معوق، بازخورد مهمان، داشبورد ادمین، تایم‌لاین، پیوست، آفلاین، دوزبانگی مهمان). از دریافت چندکاناله، QR کد اتاق و پیامک پیاده شده‌اند؛ اعلان لحظه‌ای (3.2)، تخصیص خودکار، SLA دومرحله‌ای، قالب پیامک، گزارش امتیاز، پاسخ آماده، ادغام تکراری و صفحهٔ راهنمای مهمان (همه با الهام از Odoo Helpdesk) هم پیاده شده‌اند؛ اتصال PMS (3.3) و تلویزیون اتاق (3.4) هم پیاده شده‌اند — بخش‌های «اتصال به PMS» و «تلویزیون اتاق». فاز ۳ کامل است. فاز ۴ هم پیاده شده: چت زنده (4.1)، اخبار و رویدادها (4.2) و اعلان دسکتاپ ویندوز (4.3) — بخش‌های خودشان در همین فایل. از فهرست بالا چیزی پیاده‌نشده نمانده؛ Live Chat که «اگر روزی اضافه شد» بود، اضافه شده.

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
