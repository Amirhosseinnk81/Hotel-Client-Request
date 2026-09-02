from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsGuest(BasePermission):
    """
    Allows access only to authenticated users with the GUEST role.
    """

    message = "This endpoint is for guests only."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "GUEST"
        )


class IsOperator(BasePermission):
    """
    Allows access only to authenticated users with the OPERATOR role.
    """

    message = "Only operators are allowed to access this resource."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "OPERATOR"
        )


class IsAdminRole(BasePermission):
    """
    Full access for users with role=ADMIN (or Django superusers).
    Everyone else gets read-only access if they're authenticated.

    Used for endpoints managed by hotel admins (Department, Category,
    Room, ...).
    """

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False

        if request.method in SAFE_METHODS:
            return True

        return request.user.is_superuser or request.user.role == "ADMIN"


class IsAdminOnly(BasePermission):
    """
    Admin (or Django superuser) access only — for every HTTP method,
    unlike IsAdminRole which leaves GET/HEAD/OPTIONS open to any
    authenticated user. Used for endpoints that expose cross-department
    data (e.g. admin stats) that operators/guests must never read, not
    just never write.
    """

    message = "Only admins are allowed to access this resource."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.is_superuser or request.user.role == "ADMIN")
        )
