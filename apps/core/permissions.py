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


class IsSupervisor(BasePermission):
    """
    An OPERATOR marked as their department's supervisor (User.is_supervisor).
    Supervisors triage: they assign and reassign tickets and set priority,
    on top of everything a regular operator can do.

    Always read from request.user — the database, via JWTAuthentication's
    per-request user lookup — never from the access token's
    `is_supervisor` claim. That claim exists only so the frontend knows
    which controls to show, and it goes stale: refresh rotation copies
    claims forward, so a demoted supervisor keeps `is_supervisor: true`
    in their token until they next log in. Trusting it here would let a
    demotion take up to REFRESH_TOKEN_LIFETIME to take effect.
    """

    message = "Only a department supervisor can do this."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "OPERATOR"
            and request.user.is_supervisor
        )


class CanWorkOnOperatorTicket(BasePermission):
    """
    Object-level write rules for PATCH /operator/tickets/{id}/. Always
    combined with IsOperator, and the view's queryset already limits the
    ticket to the operator's own department.

    Reading stays open to every operator in the department. Writing splits
    by access level:

    - A supervisor may change anything the serializer accepts.
    - A regular operator may only work on a ticket assigned to them, and
      only its status and resolution. Priority is triage and assigned_to
      is assignment — both are supervisor decisions.

    Checked against the raw request body rather than validated_data so a
    forbidden request is refused with 403 before validation runs, instead
    of first answering with a 400 that reveals whether the change would
    otherwise have been valid.
    """

    SUPERVISOR_ONLY_FIELDS = frozenset({"assigned_to", "priority"})

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        if request.user.is_supervisor:
            return True

        if self.SUPERVISOR_ONLY_FIELDS.intersection(request.data):
            self.message = "Only a department supervisor can change priority or assignment."
            return False

        if obj.assigned_to_id != request.user.id:
            self.message = "You can only work on tickets assigned to you."
            return False

        return True
