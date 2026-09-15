from rest_framework.permissions import BasePermission


class IsITStaff(BasePermission):
    """
    IT Ops data is internal hotel-staff data, not guest-facing.

    Only authenticated users whose `role` is "ADMIN" or "OPERATOR" (as
    stored on the User model / JWT payload) get any access (read or
    write). Guests, and anyone unauthenticated, get none.

    NOTE: this is a temporary rule for Phase 2. Phase 6 of the project
    (roles & permissions) will refine this further — e.g. restricting
    Goal creation/DepartmentRequest closing to the supervisor only
    (there's already an `is_supervisor` flag on the token payload that
    can be used for that), and scoping regular IT staff to their own
    tasks/processes.
    """

    staff_roles = {"ADMIN", "OPERATOR"}

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and getattr(user, "role", None) in self.staff_roles
        )