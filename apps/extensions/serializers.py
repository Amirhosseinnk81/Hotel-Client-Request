from rest_framework import serializers

from .models import Extension


class ExtensionSerializer(serializers.ModelSerializer):
    """
    Read and write in one serializer: staff read the directory, admins
    change it (see IsStaffReadAdminWrite).

    `department` is the real department's id; its name and working hours
    come back alongside, because the directory is read far more often
    than it is edited and the caller shouldn't have to join two lists to
    show one row.
    """

    department_name = serializers.CharField(source="department.name", read_only=True, default="")
    department_working_hours = serializers.CharField(
        source="department.working_hours", read_only=True, default=""
    )

    class Meta:
        model = Extension
        fields = (
            "id",
            "extension",
            "title",
            "person_name",
            "department",
            "department_name",
            "department_working_hours",
            "location",
            "email",
            "mobile",
            "notes",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_extension(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("The extension number is required.")
        return value
