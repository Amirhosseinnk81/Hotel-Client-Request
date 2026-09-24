/**
 * Guest-portal translations (Persian + English). No i18n library: the
 * guest portal is five client pages, and a typed dictionary covers it with
 * zero dependencies. The operator panel stays Persian-only by decision —
 * hotel staff are Iranian; it's international guests who need English.
 *
 * `en` is typed as Record<MessageKey, string>, so a key added to `fa` and
 * forgotten in `en` is a compile error, not a blank label in production.
 * Placeholders are {name}; translate() fills them.
 *
 * What is NOT translated: data typed in by the hotel (department and
 * category names, quick-request titles, operators' resolution notes) and
 * error messages that come back from the API.
 */

import type { TicketPriority, TicketStatus } from "@/lib/api/types";

export type Locale = "fa" | "en";

export const LOCALES: Locale[] = ["fa", "en"];

export function localeDir(locale: Locale): "rtl" | "ltr" {
  return locale === "fa" ? "rtl" : "ltr";
}

const fa = {
  // shell
  "app.title": "پلتفرم درخواست‌های مهمان هتل",
  "common.back": "بازگشت",
  "common.logout": "خروج",
  "common.cancel": "انصراف",
  "common.retry": "لطفاً دوباره تلاش کنید.",
  "common.genericError": "خطایی رخ داد. لطفاً دوباره تلاش کنید.",
  "common.checkingLogin": "در حال بررسی ورود…",
  "common.loading": "در حال بارگذاری…",
  "common.close": "بستن",
  "language.switchTo": "English",
  "language.switchLabel": "تغییر زبان به انگلیسی",

  // login
  "login.title": "ورود مهمان",
  "login.description": "برای ورود، کد ملی و شماره اتاق خود را وارد کنید.",
  "login.descriptionFromQr": "شماره اتاق {room} از روی کد QR وارد شد. برای ورود، کد ملی خود را هم وارد کنید.",
  "login.nationalId": "کد ملی",
  "login.roomNumber": "شماره اتاق",
  "login.nationalIdRequired": "کد ملی را وارد کنید",
  "login.roomNumberRequired": "شماره اتاق را وارد کنید",
  "login.submit": "ورود",
  "login.submitting": "در حال ورود…",

  // dashboard
  "home.welcome": "خوش آمدید",
  "home.welcomeName": "خوش آمدید، {name}",
  "home.subtitle": "پروفایل و درخواست‌های شما",
  "home.loadingProfile": "در حال بارگذاری اطلاعات…",
  "home.profileError": "خطا در دریافت اطلاعات پروفایل.",
  "home.profileTitle": "اطلاعات مهمان",
  "home.profileDescription": "اطلاعات ثبت‌شدهٔ شما نزد هتل",
  "home.fullName": "نام و نام خانوادگی",
  "home.nationalId": "کد ملی",
  "home.phone": "شماره تلفن",
  "home.room": "شماره اتاق",
  "home.requests": "درخواست‌ها",
  "home.newRequest": "ثبت درخواست جدید",
  "home.myRequests": "درخواست‌های من",
  "home.hotelInfo": "اطلاعات هتل",

  // hotel info (help page)
  "info.title": "اطلاعات هتل",
  "info.subtitle": "پاسخ سؤال‌های رایج — شاید نیازی به ثبت درخواست نباشد.",
  "info.empty": "هنوز اطلاعاتی ثبت نشده است.",
  "info.loadError": "خطا در دریافت اطلاعات هتل.",

  // list
  "list.title": "درخواست‌های من",
  "list.subtitle": "لیست درخواست‌هایی که تاکنون ثبت کرده‌اید.",
  "list.searchPlaceholder": "جستجو در عنوان یا توضیحات…",
  "list.allStatuses": "همه‌ی وضعیت‌ها",
  "list.loadError": "خطا در دریافت درخواست‌ها.",
  "list.noMatchTitle": "موردی یافت نشد",
  "list.noMatchBody": "با این فیلتر یا عبارت جست‌وجو درخواستی پیدا نشد.",
  "list.emptyTitle": "هنوز درخواستی ندارید",
  "list.emptyBody": "با ثبت اولین درخواست، اینجا نمایش داده می‌شود.",
  "list.clearFilters": "پاک‌کردن فیلترها",

  // new ticket
  "new.title": "ثبت درخواست جدید",
  "new.subtitle": "درخواست خود را برای هتل ثبت کنید.",
  "new.quick": "درخواست سریع",
  "new.infoHint": "رمز وای‌فای، ساعت صبحانه و ساعت تحویل اتاق را در «اطلاعات هتل» ببینید.",
  "new.optionsError": "خطا در دریافت لیست واحدها و دسته‌بندی‌ها.",
  "new.noDepartmentsOrCategories": "هیچ واحد و دسته‌بندی‌ای در سیستم تعریف نشده است. ابتدا از پنل مدیریت اضافه کنید.",
  "new.noDepartments": "هیچ واحدی در سیستم تعریف نشده است. ابتدا از پنل مدیریت اضافه کنید.",
  "new.noCategories": "هیچ دسته‌بندی‌ای در سیستم تعریف نشده است. ابتدا از پنل مدیریت اضافه کنید.",
  "new.fieldTitle": "عنوان",
  "new.fieldTitlePlaceholder": "مثلاً درخواست حوله اضافه",
  "new.fieldTitleMin": "عنوان باید حداقل ۳ حرف باشد",
  "new.fieldDescription": "توضیحات",
  "new.fieldDescriptionPlaceholder": "جزئیات درخواست خود را بنویسید",
  "new.fieldDescriptionMin": "توضیحات باید حداقل ۵ حرف باشد",
  "new.fieldDepartment": "واحد مربوطه",
  "new.fieldDepartmentPlaceholder": "انتخاب واحد",
  "new.fieldDepartmentRequired": "واحد را انتخاب کنید",
  "new.fieldCategory": "دسته‌بندی",
  "new.fieldCategoryPlaceholder": "انتخاب دسته‌بندی",
  "new.fieldCategoryRequired": "دسته‌بندی را انتخاب کنید",
  "new.estimatedResponse": "زمان تقریبی پاسخ: {time}",
  "new.minutes": "{n} دقیقه",
  "new.hours": "{n} ساعت",
  "new.hoursMinutes": "{h} ساعت و {m} دقیقه",
  "new.fieldPriority": "اولویت",
  "new.fieldPhoto": "عکس خرابی (اختیاری)",
  "new.choosePhoto": "انتخاب تصویر…",
  "new.submit": "ثبت درخواست",
  "new.submitting": "در حال ثبت…",
  "new.photoFailedTitle": "درخواست ثبت شد، ولی عکس پیوست نشد",
  "new.photoFailedBody": "خطا در آپلود تصویر.",
  "new.doneTitle": "درخواست شما ثبت شد",
  "new.doneBody": "«{title}» با شمارهٔ {id} برای هتل ارسال شد و به‌زودی بررسی می‌شود.",

  // detail
  "detail.backToList": "بازگشت به لیست درخواست‌ها",
  "detail.mergedInto": "این درخواست تکراری بود و با درخواست شمارهٔ {id} یکی شد؛ پیگیری آنجا ادامه دارد.",
  "detail.openMerged": "مشاهدهٔ درخواست {id}",
  "detail.notFound": "چنین درخواستی یافت نشد.",
  "detail.loadError": "خطا در دریافت جزئیات درخواست.",
  "detail.priority": "اولویت: {priority}",
  "detail.description": "توضیحات",
  "detail.attachments": "تصاویر پیوست",
  "detail.attachmentAlt": "پیوست تیکت",
  "detail.created": "ثبت‌شده:",
  "detail.updated": "آخرین به‌روزرسانی:",
  "detail.resolution": "نتیجهٔ رسیدگی",
  "detail.resolvedAt": "زمان حل:",
  "detail.yourRating": "نظر شما",
  "detail.rateQuestion": "رضایت شما از این خدمت چقدر بود؟",
  "detail.star": "{n} ستاره",
  "detail.feedbackLabel": "نظر شما (اختیاری)",
  "detail.feedbackPlaceholder": "اگر نکته‌ای هست، همین‌جا بنویسید…",
  "detail.submitRating": "ثبت نظر",
  "detail.submittingRating": "در حال ثبت…",
  "detail.thanksTitle": "متشکریم!",
  "detail.thanksBody": "نظر شما ثبت شد.",
  "detail.ratingError": "خطا در ثبت نظر",
  "detail.reopenButton": "مشکل حل نشد، دوباره باز کن",
  "detail.reopenTitle": "بازکردن دوبارهٔ درخواست",
  "detail.reopenBody": "این درخواست دوباره به وضعیت «باز» برمی‌گردد و همکاران واحد مربوطه دوباره پیگیری می‌کنند. این کار فقط یک‌بار برای هر درخواست ممکن است.",
  "detail.reopenConfirm": "بله، دوباره باز کن",
  "detail.reopening": "در حال بازکردن…",
  "detail.reopenedTitle": "درخواست دوباره باز شد",
  "detail.reopenedBody": "همکاران ما دوباره پیگیری می‌کنند.",
  "detail.reopenError": "خطا در بازکردن درخواست",

  // PDF button
  "pdf.button": "دریافت PDF",
  "pdf.error": "دریافت PDF ناموفق بود",

  // theme
  "theme.toLight": "تغییر به حالت روشن",
  "theme.toDark": "تغییر به حالت تاریک",

  // time
  "time.now": "اکنون",

  // ticket labels
  "status.OPEN": "باز",
  "status.IN_PROGRESS": "در حال بررسی",
  "status.RESOLVED": "حل‌شده",
  "status.CANCELLED": "لغوشده",
  "priority.LOW": "کم",
  "priority.NORMAL": "عادی",
  "priority.HIGH": "زیاد",
  "priority.URGENT": "فوری",
} as const;

export type MessageKey = keyof typeof fa;

const en: Record<MessageKey, string> = {
  "app.title": "Hotel Guest Requests",
  "common.back": "Back",
  "common.logout": "Log out",
  "common.cancel": "Cancel",
  "common.retry": "Please try again.",
  "common.genericError": "Something went wrong. Please try again.",
  "common.checkingLogin": "Checking your sign-in…",
  "common.loading": "Loading…",
  "common.close": "Close",
  "language.switchTo": "فارسی",
  "language.switchLabel": "Switch language to Persian",

  "login.title": "Guest sign-in",
  "login.description": "Enter your national ID (or passport number) and room number to sign in.",
  "login.descriptionFromQr": "Room {room} was filled in from the QR code. Enter your national ID (or passport number) to sign in.",
  "login.nationalId": "National ID / passport number",
  "login.roomNumber": "Room number",
  "login.nationalIdRequired": "Enter your national ID or passport number",
  "login.roomNumberRequired": "Enter your room number",
  "login.submit": "Sign in",
  "login.submitting": "Signing in…",

  "home.welcome": "Welcome",
  "home.welcomeName": "Welcome, {name}",
  "home.subtitle": "Your profile and requests",
  "home.loadingProfile": "Loading your details…",
  "home.profileError": "Could not load your profile.",
  "home.profileTitle": "Guest details",
  "home.profileDescription": "The details the hotel has on file for you",
  "home.fullName": "Full name",
  "home.nationalId": "National ID / passport",
  "home.phone": "Phone number",
  "home.room": "Room number",
  "home.requests": "Requests",
  "home.newRequest": "New request",
  "home.myRequests": "My requests",
  "home.hotelInfo": "Hotel info",

  "info.title": "Hotel information",
  "info.subtitle": "Quick answers — you may not need to send a request at all.",
  "info.empty": "Nothing here yet.",
  "info.loadError": "Could not load the hotel information.",

  "list.title": "My requests",
  "list.subtitle": "Every request you have made so far.",
  "list.searchPlaceholder": "Search title or details…",
  "list.allStatuses": "All statuses",
  "list.loadError": "Could not load your requests.",
  "list.noMatchTitle": "Nothing found",
  "list.noMatchBody": "No request matches this filter or search.",
  "list.emptyTitle": "No requests yet",
  "list.emptyBody": "Your first request will show up here.",
  "list.clearFilters": "Clear filters",

  "new.title": "New request",
  "new.subtitle": "Tell the hotel what you need.",
  "new.quick": "Quick requests",
  "new.infoHint": "The Wi-Fi password, breakfast hours and check-out time are in Hotel info.",
  "new.optionsError": "Could not load the departments and categories.",
  "new.noDepartmentsOrCategories": "No departments or categories are set up yet. Please contact the front desk.",
  "new.noDepartments": "No departments are set up yet. Please contact the front desk.",
  "new.noCategories": "No categories are set up yet. Please contact the front desk.",
  "new.fieldTitle": "Title",
  "new.fieldTitlePlaceholder": "e.g. Extra towels",
  "new.fieldTitleMin": "The title needs at least 3 characters",
  "new.fieldDescription": "Details",
  "new.fieldDescriptionPlaceholder": "Tell us a little more",
  "new.fieldDescriptionMin": "The details need at least 5 characters",
  "new.fieldDepartment": "Department",
  "new.fieldDepartmentPlaceholder": "Choose a department",
  "new.fieldDepartmentRequired": "Choose a department",
  "new.fieldCategory": "Category",
  "new.fieldCategoryPlaceholder": "Choose a category",
  "new.fieldCategoryRequired": "Choose a category",
  "new.estimatedResponse": "Estimated response time: {time}",
  "new.minutes": "{n} min",
  "new.hours": "{n} h",
  "new.hoursMinutes": "{h} h {m} min",
  "new.fieldPriority": "Priority",
  "new.fieldPhoto": "Photo of the problem (optional)",
  "new.choosePhoto": "Choose a photo…",
  "new.submit": "Send request",
  "new.submitting": "Sending…",
  "new.photoFailedTitle": "Request sent, but the photo was not attached",
  "new.photoFailedBody": "The photo could not be uploaded.",
  "new.doneTitle": "Your request has been sent",
  "new.doneBody": "“{title}” was sent to the hotel as request #{id} and will be looked at shortly.",

  "detail.backToList": "Back to my requests",
  "detail.mergedInto": "This was a duplicate and was merged into request #{id}; it is being handled there.",
  "detail.openMerged": "Open request #{id}",
  "detail.notFound": "This request could not be found.",
  "detail.loadError": "Could not load this request.",
  "detail.priority": "Priority: {priority}",
  "detail.description": "Details",
  "detail.attachments": "Attached photos",
  "detail.attachmentAlt": "Request attachment",
  "detail.created": "Sent:",
  "detail.updated": "Last updated:",
  "detail.resolution": "What we did",
  "detail.resolvedAt": "Resolved:",
  "detail.yourRating": "Your rating",
  "detail.rateQuestion": "How satisfied were you with this service?",
  "detail.star": "{n} stars",
  "detail.feedbackLabel": "Your comments (optional)",
  "detail.feedbackPlaceholder": "Anything you'd like to add…",
  "detail.submitRating": "Send rating",
  "detail.submittingRating": "Sending…",
  "detail.thanksTitle": "Thank you!",
  "detail.thanksBody": "Your rating has been recorded.",
  "detail.ratingError": "Could not send your rating",
  "detail.reopenButton": "Not fixed — reopen",
  "detail.reopenTitle": "Reopen this request",
  "detail.reopenBody": "The request goes back to “Open” and the department will follow it up again. You can do this only once per request.",
  "detail.reopenConfirm": "Yes, reopen it",
  "detail.reopening": "Reopening…",
  "detail.reopenedTitle": "Request reopened",
  "detail.reopenedBody": "Our team will follow it up again.",
  "detail.reopenError": "Could not reopen the request",

  "pdf.button": "Download PDF",
  "pdf.error": "Could not download the PDF",

  "theme.toLight": "Switch to light mode",
  "theme.toDark": "Switch to dark mode",

  "time.now": "just now",

  "status.OPEN": "Open",
  "status.IN_PROGRESS": "In progress",
  "status.RESOLVED": "Resolved",
  "status.CANCELLED": "Cancelled",
  "priority.LOW": "Low",
  "priority.NORMAL": "Normal",
  "priority.HIGH": "High",
  "priority.URGENT": "Urgent",
};

export const messages: Record<Locale, Record<MessageKey, string>> = { fa, en };

export function translate(
  locale: Locale,
  key: MessageKey,
  vars?: Record<string, string | number>
): string {
  const template = messages[locale][key];
  if (!vars) return template;
  return template.replace(/\{(\w+)\}/g, (match, name: string) =>
    name in vars ? String(vars[name]) : match
  );
}

/** Dictionary keys for the ticket labels (lib/ticket-labels.ts has the Persian originals). */
export const statusMessageKey = (status: TicketStatus) => `status.${status}` as const;
export const priorityMessageKey = (priority: TicketPriority) => `priority.${priority}` as const;
