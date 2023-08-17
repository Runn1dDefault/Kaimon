from rest_framework.permissions import BasePermission


def user_has_prem(user) -> bool:
    return user.is_authenticated  # TODO: and user.registration_payed


class RegistrationPayedPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        return user_has_prem(request.user)

    def has_permission(self, request, view):
        return user_has_prem(request.user)
