from rest_framework.permissions import BasePermission


class RegistrationPayedPermission(BasePermission):
    """
    to check the status of the authorized user's payment for registration
    """
    def has_permission(self, request, view):
        return request.user and request.user.registration_payed


class EmailConfirmedPermission(BasePermission):

    def has_permission(self, request, view):
        return request.user and request.user.email_confirmed


class IsDirector(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_director


class IsStaffUser(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_active:
            return False
        return request.user.is_developer or request.user.is_director or request.user.is_manager


class IsAuthor(BasePermission):
    user_field_param = 'user_field'

    def get_user_field(self, view):
        return getattr(view, self.user_field_param, 'user')

    def has_object_permission(self, request, view, obj):
        return getattr(obj, self.get_user_field(view)) == request.user
