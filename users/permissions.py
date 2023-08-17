from rest_framework.permissions import IsAuthenticated


class RegistrationPayedPermission(IsAuthenticated):
    """
    to check the status of the authorized user's payment for registration
    """
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.registration_payed
