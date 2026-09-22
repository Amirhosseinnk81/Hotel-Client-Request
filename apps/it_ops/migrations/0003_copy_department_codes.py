from django.db import migrations

# The old it_ops.Department choice list, mapped onto the codes that
# seed_demo_data (and so a normal install) uses for departments.Department.
# Anything that matches no existing department becomes NULL rather than
# inventing a department nobody created.
LEGACY_CODE_ALIASES = {
    "F_AND_B": "ROOM_SERVICE",
}


def copy_department_codes(apps, schema_editor):
    Department = apps.get_model("departments", "Department")
    Process = apps.get_model("it_ops", "Process")
    DepartmentRequest = apps.get_model("it_ops", "DepartmentRequest")

    by_code = {dept.code: dept for dept in Department.objects.all()}

    def resolve(code):
        if not code:
            return None
        return by_code.get(code) or by_code.get(LEGACY_CODE_ALIASES.get(code, ""))

    for process in Process.objects.all():
        process.department_ref = resolve(process.department)
        process.save(update_fields=["department_ref"])

    for request in DepartmentRequest.objects.all():
        request.requesting_department_ref = resolve(request.requesting_department)
        request.save(update_fields=["requesting_department_ref"])


def copy_department_codes_back(apps, schema_editor):
    Process = apps.get_model("it_ops", "Process")
    DepartmentRequest = apps.get_model("it_ops", "DepartmentRequest")

    for process in Process.objects.select_related("department_ref"):
        process.department = process.department_ref.code if process.department_ref else "IT"
        process.save(update_fields=["department"])

    for request in DepartmentRequest.objects.select_related("requesting_department_ref"):
        request.requesting_department = (
            request.requesting_department_ref.code if request.requesting_department_ref else "OTHER"
        )
        request.save(update_fields=["requesting_department"])


class Migration(migrations.Migration):
    """
    Carries the old department codes over to the new FKs added in 0002.
    Its own migration (so its own transaction): PostgreSQL refuses to
    ALTER a table that still has pending FK trigger events from rows
    updated in the same transaction.
    """

    dependencies = [
        ("it_ops", "0002_real_departments_and_schedule"),
    ]

    operations = [
        migrations.RunPython(copy_department_codes, copy_department_codes_back),
    ]
