from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import User
from apps.departments.models import Department
from apps.guests.models import Guest
from apps.rooms.models import Room
from apps.tickets.models import Category, QuickRequestTemplate

DEPARTMENTS = [
    {"name": "خانه‌داری", "code": "HOUSEKEEPING"},
    {"name": "پذیرش", "code": "FRONT_DESK"},
    {"name": "فنی و تعمیرات", "code": "MAINTENANCE"},
    {"name": "خدمات اتاق و رستوران", "code": "ROOM_SERVICE"},
    {"name": "کنسیرژ", "code": "CONCIERGE"},
]

# (name, code, sla_minutes, department_code) — department_code is only used
# below to pick a sensible operator/quick-template pairing; Category itself
# has no FK to Department.
CATEGORIES = [
    ("حوله/ملحفهٔ اضافه", "TOWELS", 15, "HOUSEKEEPING"),
    ("بالش/پتوی اضافه", "BEDDING", 15, "HOUSEKEEPING"),
    ("نظافت اتاق", "ROOM_CLEANING", 45, "HOUSEKEEPING"),
    ("نظافت فوری", "QUICK_CLEAN", 20, "HOUSEKEEPING"),
    ("سرویس لباسشویی", "LAUNDRY", 120, "HOUSEKEEPING"),
    ("مشکل تهویه/دما", "AC_TEMP", 20, "MAINTENANCE"),
    ("خرابی برق/پریز", "ELECTRICAL", 15, "MAINTENANCE"),
    ("خرابی تلویزیون", "TV_ISSUE", 20, "MAINTENANCE"),
    ("مشکل اینترنت/وای‌فای", "WIFI_ISSUE", 15, "MAINTENANCE"),
    ("مشکل تلفن اتاق", "PHONE_ISSUE", 15, "MAINTENANCE"),
    ("لوله‌کشی/سرویس بهداشتی", "PLUMBING", 30, "MAINTENANCE"),
    ("سفارش روم‌سرویس", "ROOM_SERVICE_ORDER", 40, "ROOM_SERVICE"),
    ("درخواست مینی‌بار", "MINIBAR", 20, "ROOM_SERVICE"),
    ("بیدارباش", "WAKE_UP_CALL", 10, "FRONT_DESK"),
    ("تحویل/جابه‌جایی بار", "LUGGAGE", 15, "FRONT_DESK"),
    ("درخواست عمومی/شکایت", "GENERAL", 30, "CONCIERGE"),
]

# (title, icon, category_code, department_code, order)
QUICK_TEMPLATES = [
    ("آب معدنی", "Droplet", "MINIBAR", "ROOM_SERVICE", 1),
    ("حولهٔ اضافه", "Sparkles", "TOWELS", "HOUSEKEEPING", 2),
    ("بالش اضافه", "BedDouble", "BEDDING", "HOUSEKEEPING", 3),
    ("نظافت فوری", "Sparkles", "QUICK_CLEAN", "HOUSEKEEPING", 4),
    ("مشکل تهویه", "Wind", "AC_TEMP", "MAINTENANCE", 5),
    ("منوی روم‌سرویس", "UtensilsCrossed", "ROOM_SERVICE_ORDER", "ROOM_SERVICE", 6),
]

# (floor, numbers, status)
ROOM_LAYOUT = [
    ("1", [f"10{n}" for n in range(1, 11)], Room.Status.AVAILABLE),
    ("2", [f"20{n}" if n < 10 else f"2{n}" for n in range(1, 11)], Room.Status.AVAILABLE),
]
# Rooms that get flipped to OCCUPIED (needed for guest login) / MAINTENANCE.
OCCUPIED_ROOM_NUMBERS = ["101", "102", "103", "104", "105", "201"]
MAINTENANCE_ROOM_NUMBERS = ["110", "210"]

# (username, password, department_code)
OPERATORS = [
    ("op_housekeeping", "ZZzz123!@#", "HOUSEKEEPING"),
    ("op_frontdesk", "ZZzz123!@#", "FRONT_DESK"),
    ("op_maintenance", "ZZzz123!@#", "MAINTENANCE"),
    ("op_roomservice", "ZZzz123!@#", "ROOM_SERVICE"),
    ("op_concierge", "ZZzz123!@#", "CONCIERGE"),
]
ADMIN_USERNAME = "hotel_admin"
ADMIN_PASSWORD = "Demo!Pass123"

# (full_name, national_id, phone, room_number)
GUESTS = [
    ("سارا احمدی", "0011122233", "09121112233", "101"),
    ("علی رضایی", "0011122234", "09121112234", "102"),
    ("مریم کریمی", "0011122235", "09121112235", "103"),
    ("حسین محمدی", "0011122236", "09121112236", "104"),
    ("نگار حسینی", "0011122237", "09121112237", "105"),
    ("امیر جعفری", "0011122238", "09121112238", "201"),
]


class Command(BaseCommand):
    help = (
        "Seeds demo data for local/staging use: departments, categories "
        "(with SLA minutes), rooms, one admin + one operator per "
        "department, sample guests, and quick-request templates. Safe to "
        "run more than once — every record is get_or_create'd, so re-runs "
        "only fill in whatever's still missing."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset-passwords",
            action="store_true",
            help=(
                "Also reset the password of any admin/operator accounts "
                "that already exist, instead of leaving them untouched."
            ),
        )

    @transaction.atomic
    def handle(self, *args, **options):
        departments = self._seed_departments()
        categories = self._seed_categories()
        self._seed_rooms()
        self._seed_users(departments, options["reset_passwords"])
        self._seed_guests()
        self._seed_quick_templates(departments, categories)

        self.stdout.write(self.style.SUCCESS("Demo data seeded."))

    # -- departments ---------------------------------------------------

    def _seed_departments(self):
        departments = {}
        for entry in DEPARTMENTS:
            dept, created = Department.objects.get_or_create(
                code=entry["code"], defaults={"name": entry["name"]}
            )
            departments[entry["code"]] = dept
            self._log(created, "Department", dept.name)
        return departments

    # -- categories ------------------------------------------------------

    def _seed_categories(self):
        categories = {}
        for name, code, sla_minutes, _dept_code in CATEGORIES:
            category, created = Category.objects.get_or_create(
                code=code, defaults={"name": name, "sla_minutes": sla_minutes}
            )
            if not created and category.sla_minutes != sla_minutes:
                category.sla_minutes = sla_minutes
                category.name = name
                category.save(update_fields=["sla_minutes", "name"])
            categories[code] = category
            self._log(created, "Category", f"{category.name} (SLA {sla_minutes}m)")
        return categories

    # -- rooms -------------------------------------------------------------

    def _seed_rooms(self):
        for floor, numbers, default_status in ROOM_LAYOUT:
            for number in numbers:
                status = default_status
                if number in OCCUPIED_ROOM_NUMBERS:
                    status = Room.Status.OCCUPIED
                elif number in MAINTENANCE_ROOM_NUMBERS:
                    status = Room.Status.MAINTENANCE

                room, created = Room.objects.get_or_create(
                    number=number, defaults={"floor": floor, "status": status}
                )
                if not created and room.status != status:
                    room.status = status
                    room.save(update_fields=["status"])
                self._log(created, "Room", f"{room.number} ({room.get_status_display()})")

    # -- users (admin + operators) -----------------------------------------

    def _seed_users(self, departments, reset_passwords):
        admin, created = User.objects.get_or_create(
            username=ADMIN_USERNAME,
            defaults={"role": User.Role.ADMIN, "is_staff": True, "is_superuser": True},
        )
        if created or reset_passwords:
            admin.set_password(ADMIN_PASSWORD)
            admin.is_staff = True
            admin.is_superuser = True
            admin.role = User.Role.ADMIN
            admin.save()
        self._log(created, "Admin user", f"{admin.username} / {ADMIN_PASSWORD}")

        for username, password, dept_code in OPERATORS:
            operator, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "role": User.Role.OPERATOR,
                    "department": departments[dept_code],
                    "is_available": True,
                },
            )
            if created or reset_passwords:
                operator.set_password(password)
                operator.role = User.Role.OPERATOR
                operator.department = departments[dept_code]
                operator.save()
            self._log(created, "Operator", f"{operator.username} / {password} ({dept_code})")

    # -- guests --------------------------------------------------------------

    def _seed_guests(self):
        for full_name, national_id, phone, room_number in GUESTS:
            room = Room.objects.filter(number=room_number).first()
            if room is None:
                self.stdout.write(
                    self.style.WARNING(
                        f"  skip guest {full_name}: room {room_number} not found"
                    )
                )
                continue

            guest = Guest.objects.filter(national_id=national_id).first()
            if guest is not None:
                self._log(False, "Guest", f"{guest.full_name} (room {room_number})")
                continue

            # Guests authenticate by national_id + room number, not a
            # password (see GuestLoginSerializer) — the linked User just
            # needs to exist with role=GUEST; give it an unusable password
            # so it can never log in through the operator/admin form.
            user = User.objects.create(username=f"guest_{national_id}", role=User.Role.GUEST)
            user.set_unusable_password()
            user.save()

            guest = Guest.objects.create(
                user=user,
                full_name=full_name,
                national_id=national_id,
                phone=phone,
                room=room,
            )
            self._log(True, "Guest", f"{guest.full_name} (room {room_number})")

    # -- quick request templates --------------------------------------------

    def _seed_quick_templates(self, departments, categories):
        for title, icon, category_code, dept_code, order in QUICK_TEMPLATES:
            template, created = QuickRequestTemplate.objects.get_or_create(
                title=title,
                defaults={
                    "icon": icon,
                    "department": departments[dept_code],
                    "category": categories[category_code],
                    "order": order,
                },
            )
            self._log(created, "Quick template", template.title)

    # -- helpers -------------------------------------------------------------

    def _log(self, created, kind, label):
        marker = self.style.SUCCESS("created") if created else self.style.WARNING("exists")
        self.stdout.write(f"  [{marker}] {kind}: {label}")
