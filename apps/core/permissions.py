from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAdminRole(BasePermission):
    """
    Full access for users with role=ADMIN (or Django superusers).
    Everyone else gets read-only access if they're authenticated.

    Used for endpoints managed by hotel admins (Department, Category, ...).
    """

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False

        if request.method in SAFE_METHODS:
            return True

        return request.user.is_superuser or request.user.role == "ADMIN"