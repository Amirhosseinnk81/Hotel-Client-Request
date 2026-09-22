from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User


class OperatorTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Operator login: standard username + password, but only accounts with
    role OPERATOR or ADMIN are allowed to obtain a token here.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        token["username"] = user.username
        # UI hint only — tells the frontend whether to show assignment and
        # priority controls. Never used for authorization: IsSupervisor
        # re-reads the flag from the database on every request, because
        # refresh rotation copies this claim forward unchanged and it can
        # lag behind a promotion or demotion until the next login.
        token["is_supervisor"] = user.is_supervisor
        # Same kind of UI hint: lets the panel show the IT Ops link to IT
        # staff. IsITStaff re-reads the department from the database.
        token["department_code"] = user.department.code if user.department_id else None
        return token

    def validate(self, attrs):
        data = super().validate(attrs)

        if self.user.role not in (User.Role.OPERATOR, User.Role.ADMIN):
            raise serializers.ValidationError(
                "This login is for operators only."
            )

        data["role"] = self.user.role
        return data


class OperatorAvailabilitySerializer(serializers.Serializer):
    """
    GET /api/v1/operator/me/status/ — the logged-in operator's own status.

    Read-only and derived, never stored: busy while any ticket assigned to
    them is still OPEN or IN_PROGRESS, available once none are (see
    apps.tickets.services.active_ticket_count). There is deliberately no
    way to set it by hand — a manual toggle is exactly what let "busy" and
    reality drift apart.
    """

    is_available = serializers.BooleanField(read_only=True)
    active_tickets = serializers.IntegerField(read_only=True)