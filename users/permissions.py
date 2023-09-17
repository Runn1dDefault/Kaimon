from rest_framework.permissions import BasePermission, IsAuthenticated


class RegistrationPayedPermission(IsAuthenticated):
    """
    to check the status of the authorized user's payment for registration
    """
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.registration_payed


class EmailConfirmedPermission(IsAuthenticated):

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.email_confirmed


class IsDirectorPermission(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_director


class IsStaffUser(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated or not request.user.is_active:
            return False
        return request.user.is_developer or request.user.is_director or request.user.is_manager
