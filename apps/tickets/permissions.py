from rest_framework.permissions import BasePermission

from apps.accounts.models import User


class IsOperator(BasePermission):
    """
    Allows access only to authenticated users
    with the OPERATOR role.
    """

    message = "Only operators are allowed to access this resource."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == User.Role.OPERATOR
        )