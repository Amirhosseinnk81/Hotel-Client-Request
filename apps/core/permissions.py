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


class IsStaffReadAdminWrite(BasePermission):
    """
    Any member of staff may read; only admins may change.

    Deliberately NOT IsAdminRole, which leaves reading open to every
    authenticated user — and guests are authenticated users. Used for
    the staff phone directory (apps/extensions), which carries staff
    names, mobiles and locations: hotel staff look people up all day,
    guests have no business reading it.
    """

    message = "Only hotel staff may read this, and only admins may change it."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False

        is_admin = request.user.is_superuser or request.user.role == "ADMIN"
        if request.method in SAFE_METHODS:
            return is_admin or request.user.role == "OPERATOR"
        return is_admin


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


# ---------------------------------------------------------------------------
# IT Ops (apps.it_ops)
#
# IT staff are not a new role: they are OPERATORs whose department is the IT
# department (code settings.IT_DEPARTMENT_CODE, default "IT"), and the IT
# supervisor is simply the IT operator with is_supervisor — the same
# three-level model as the ticket side. Admins get supervisor-level access.
# Like IsSupervisor, everything is read from request.user (the database),
# never from token claims.
# ---------------------------------------------------------------------------


def it_department_code():
    from django.conf import settings

    return getattr(settings, "IT_DEPARTMENT_CODE", "IT")


def _is_admin(user):
    return bool(user.is_superuser or user.role == "ADMIN")


def is_it_operator(user):
    """An OPERATOR in the IT department (regular or supervisor)."""
    return bool(
        user
        and user.is_authenticated
        and user.role == "OPERATOR"
        and user.department_id is not None
        and user.department.code == it_department_code()
    )


def is_it_staff(user):
    return bool(user and user.is_authenticated and (_is_admin(user) or is_it_operator(user)))


def is_it_supervisor(user):
    return bool(
        user
        and user.is_authenticated
        and (_is_admin(user) or (is_it_operator(user) and user.is_supervisor))
    )


class IsOperatorWithDepartment(BasePermission):
    """
    Any OPERATOR who belongs to a department — for endpoints scoped to
    "my own department" (e.g. filing a request to IT). An operator with no
    department is refused rather than treated as "every department",
    the same rule as the department stats summary.
    """

    message = "Only an operator with a department can do this."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.role == "OPERATOR"
            and user.department_id is not None
        )


class IsITStaff(BasePermission):
    """
    Any access to IT Ops data at all: IT operators and admins. An operator
    of any other department (housekeeping, front desk, ...) gets 403 even
    for GET — this is internal IT data, not a hotel-wide board.
    """

    message = "Only IT staff can access IT Ops."

    def has_permission(self, request, view):
        return is_it_staff(request.user)


class CanWorkOnITItem(BasePermission):
    """
    Write rules for the IT Ops ViewSets, always combined with IsITStaff.
    Mirrors CanWorkOnOperatorTicket on the ticket side:

    - Reading is open to all IT staff.
    - The IT supervisor (and admins) may create, change and delete anything.
    - A regular IT operator may only work on items assigned to them
      (view.it_assignee_field: "assigned_to" / "responsible"), never change
      view.it_supervisor_only_fields, never set a value listed in
      view.it_supervisor_only_values, and never delete. Where the view sets
      it_staff_can_create, they may also create — but not on someone
      else's behalf.

    Checked against the raw request body so a forbidden change is refused
    with 403 before validation runs (same reasoning as
    CanWorkOnOperatorTicket).
    """

    message = "Only the IT supervisor can do this."

    def _forbidden_body(self, request, view, allowed=()):
        data = request.data
        for field in getattr(view, "it_supervisor_only_fields", ()):
            if field in data and field not in allowed:
                return f"Only the IT supervisor can change {field}."
        for field, values in getattr(view, "it_supervisor_only_values", {}).items():
            if data.get(field) in values:
                return f"Only the IT supervisor can set {field} to {data.get(field)}."
        return None

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS or is_it_supervisor(request.user):
            return True

        action = getattr(view, "action", None)
        if action != "create":
            # Updates, deletes and detail actions are decided per object;
            # a list-level write action (e.g. room-stats/snapshot/) has no
            # object to decide on, so it stays supervisor-only.
            return bool(getattr(view, "detail", False))

        if not getattr(view, "it_staff_can_create", False):
            return False

        # Creating for yourself is fine; assigning to someone else isn't.
        assignee_field = getattr(view, "it_assignee_field", None)
        if assignee_field and assignee_field in request.data:
            value = request.data.get(assignee_field)
            if value not in (None, "", request.user.pk, str(request.user.pk)):
                self.message = "Only the IT supervisor can assign work to someone else."
                return False

        # A new item may carry its own priority (like a guest's ticket);
        # only supervisor-only *values* (e.g. filing it straight as
        # REJECTED) are refused on create.
        every_field = tuple(getattr(view, "it_supervisor_only_fields", ()))
        reason = self._forbidden_body(request, view, allowed=every_field)
        if reason:
            self.message = reason
            return False
        return True

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS or is_it_supervisor(request.user):
            return True

        if request.method == "DELETE":
            return False

        assignee_field = getattr(view, "it_assignee_field", None)
        if assignee_field is None:
            return False

        if getattr(obj, f"{assignee_field}_id") != request.user.pk:
            self.message = "You can only work on IT items assigned to you."
            return False

        # Some views let the assignee use only specific actions (a process's
        # responsible person may mark it done, not rewrite its schedule).
        assignee_actions = getattr(view, "it_assignee_actions", None)
        if assignee_actions is not None and getattr(view, "action", None) not in assignee_actions:
            return False

        reason = self._forbidden_body(request, view)
        if reason:
            self.message = reason
            return False
        return True
