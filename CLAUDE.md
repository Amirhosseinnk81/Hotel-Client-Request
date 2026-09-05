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
| تست بک‌اند | Django `TestCase`/`APITestCase` روی PostgreSQL واقعی — **۱۵۶ تست** |
| تست فرانت | Vitest + React Testing Library — **۳۳ تست** |
| Deployment | مستقیم روی هاست ویندوز، بدون Docker/Redis/Celery |

## دستورهای رایج

```bash
# بک‌اند (از ریشهٔ ریپو)
python manage.py migrate
python manage.py runserver localhost:8000      # localhost، نه 127.0.0.1 — بخش «دو تلهٔ همیشگی»
python manage.py seed_demo_data                # دادهٔ دموی فارسی: واحدها، دسته‌ها، اتاق، اپراتور، مهمان
python manage.py seed_demo_data --reset-passwords
python manage.py test                          # کل ۱۵۶ تست
python manage.py test apps.tickets             # فقط یک اپ
python manage.py spectacular --file Hotel_Client_Request_Platform_API.yaml
```

اجرای یک تست منفرد:

```bash
python manage.py test apps.tickets.tests.OperatorTicketTests.test_operator_can_cancel_open_ticket
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
  - `accounts/` — User سفارشی (`role`، `department`، `is_available`)، لاگین اپراتور، refresh، logout
  - `guests/` — Guest و لاگین مهمان
  - `rooms/` — Room و `RoomStatusLog` (لاگ append-only که خودِ `Room.save()` می‌نویسد)
  - `departments/` — CRUD ادمین
  - `tickets/` — هستهٔ پروژه: `Category`، `Ticket`، `TicketHistory`، `TicketNote`، `TicketAttachment`، `QuickRequestTemplate`، و `pdf.py`
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

`Category.sla_minutes` (پیش‌فرض ۶۰) تنها عدد قابل تنظیم است و **دو کاربرد همزمان** دارد: «زمان تخمینی پاسخ» که به مهمان نشان داده می‌شود، و هایلایت «معوق» در داشبورد اپراتور. عمداً یک عدد است نه دو تا، که از هم درنروند. تیکت `RESOLVED`/`CANCELLED` هرگز معوق حساب نمی‌شود (`Ticket.is_overdue`).

## خروجی PDF تیکت

`GET /api/v1/tickets/{id}/export/pdf/` — پاسخ `application/pdf` است نه JSON. دسترسی: هرکس که از قبل از مسیر دیگری هم می‌توانست همان تیکت را ببیند (مهمان صاحب تیکت، اپراتور همان واحد، ادمین). برای عدم تطابق عمداً **۴۰۴ برمی‌گردد نه ۴۰۳**، تا وجود تیکت دیگران لو نرود — هم‌راستا با `GuestTicketDetailView` و `OperatorTicketDetailView`.

منطق تولید در `apps/tickets/pdf.py`. دو نکته که قبلاً وقت زیادی از ما گرفت و در کد فعلی درست پیاده شده — خرابش نکن:

- **فونت:** از فونت «Non-Latin» پکیج Vazirmatn استفاده نکن؛ گلیف حروف لاتین و ارقام ASCII را ندارد و شمارهٔ اتاق و username خالی چاپ می‌شوند. فونت کامل `apps/tickets/assets/fonts/Vazirmatn-{Regular,Bold}.ttf` (لایسنس OFL کنارش هست) درست است.
- **Shaping:** reportlab خودش RTL و جوین حروف را مدیریت نمی‌کند؛ باید با `arabic-reshaper` + `python-bidi` شکل داده شود. **word-wrap باید روی متن unshaped انجام شود و بعد هر خط جداگانه shape شود** — اگر متن shape‌شده را wrap کنی ترتیب حروف به هم می‌ریزد. الگویش در `_wrap_lines` و `_shape` است.

## Dark Mode

کلاس‌محور است: `ThemeProvider` در `frontend/src/contexts/theme-context.tsx` کلاس `dark` را روی `<html>` می‌گذارد و انتخاب کاربر را در `localStorage` نگه می‌دارد. در Tailwind v4 با `@custom-variant dark (&:is(.dark *))` در `globals.css` وصل شده. پالت تیره عمداً همان هویت رنگی teal/brass را نگه می‌دارد، نه یک وارونه‌سازی خاکستری/مشکی.

## تاریخچهٔ وضعیت اتاق

`RoomStatusLog` را خودِ `Room.save()` می‌نویسد — append-only، هیچ‌جا آپدیت یا حذف نمی‌شود. خواندنش از `GET /api/v1/rooms/{id}/status-logs/`. سریالایزرش عمداً فقط‌خواندنی است.

## الگوهای جاافتاده — اینها را تکرار کن، چیز نو اختراع نکن

**بک‌اند**

- پرمیشن‌ها فقط از `apps/core/permissions.py`. تفاوت حیاتی: `IsAdminRole` نوشتن را به ادمین محدود می‌کند ولی **خواندن را برای هر کاربر لاگین‌شده باز می‌گذارد**؛ `IsAdminOnly` حتی GET را هم می‌بندد. هر endpointی که دادهٔ بین‌واحدی می‌دهد (مثل `admin/stats/summary/`) باید `IsAdminOnly` باشد — اشتباه گرفتن این دو یعنی افشای دادهٔ واحدهای دیگر به اپراتور.
- تغییر مدل → `makemigrations <app>`.
- تغییر API → دوباره `spectacular` بزن. فایل YAML دستی ادیت نمی‌شود.
- منطق غیر-CRUD برود در `services.py` (نمونه: `compute_admin_stats_summary`)، نه داخل view.
- همهٔ اپ‌ها `app_name` دارند و مسیرهایشان namespace‌دار است. تست‌های `apps/tickets/tests.py` هنوز آدرس‌ها را به‌صورت رشتهٔ ثابت (`"/api/v1/operator/tickets/"`) می‌نویسند، چون این اپ تا همین اواخر `app_name` نداشت؛ بقیهٔ اپ‌ها از `reverse("<app>:<name>")` استفاده می‌کنند. تست جدید که می‌نویسی از `reverse("tickets:...")` استفاده کن.

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

لاگین مهمان رمز عبور ندارد، پس تنها ترمز حدس‌زدن `national_id` / `room_number` همان throttle است: `guest_login`، پیش‌فرض `10/min`، تنظیم‌شدنی با `GUEST_LOGIN_THROTTLE_RATE`.

## باگ‌های قبلی — دوباره تکرار نکن

- **آپلود فایل در `apiFetch`:** پیش از ست‌کردن `Content-Type: application/json` حتماً `instanceof FormData` چک شود، وگرنه آپلود چندبخشی بی‌صدا خراب می‌شود. الان درست است — خرابش نکن.
- **`read_only_fields = fields`:** اگر سریالایزر قرار است داده هم بپذیرد، این باعث می‌شود ورودی بی‌صدا و بدون خطای validation دور ریخته شود. فقط برای سریالایزرهای صرفاً خواندنی درست است (مثل `RoomStatusLogSerializer`).
- **Pagination:** `PageNumberPagination` با `PAGE_SIZE=10` به‌صورت پیش‌فرض روی همهٔ لیست‌هاست. تستی که فرض کند `response.data` مستقیماً لیست است بی‌صدا فیل می‌شود؛ باید `response.data["results"]` باز شود.
- **حذف پوشهٔ عمیق در ویندوز:** `cmd /c rmdir /s /q node_modules` — نه `Remove-Item` در PowerShell (قفل‌شدن فایل).
- **کش `.next`:** بعد از تغییر ساختاری، اگر خطای عجیب TypeScript روی `routes.d.ts` دیدی، `.next` را کامل پاک کن.
- **مرج دستی:** وقتی Amirhossein خودش یک Stage را پیاده می‌کند، فیچرهای تأییدشدهٔ قبلی دوباره چک شوند — یک‌بار فیچر تأییدشده از بین رفته.

## قبل از تحویل هر تغییر — Verification Gate

بدون استثنا و به همین ترتیب:

1. بک‌اند تغییر کرده؟ `python manage.py test` **کامل** روی PostgreSQL 16 واقعی — نه فقط اپ تغییریافته، نه SQLite.
2. فرانت‌اند تغییر کرده؟ هر سه باید سبز باشند: `npm run lint` ، `npm run build` ، `npm test`.
3. فقط فایل‌های تغییریافته/جدید را با جدول شماره‌گذاری‌شده (مسیر واقعی ← نام فایل تحویلی) تحویل بده، نه کل ریپو.
4. صبر کن Amirhossein روی مرورگر واقعی دستی تأیید کند، بعد سراغ Stage بعدی برو.

انتقال فایل بین دو ماشین ویندوز دستی انجام می‌شود و از اینجا `git push` زده نمی‌شود — این نسخه اصلاً `.git` ندارد.
