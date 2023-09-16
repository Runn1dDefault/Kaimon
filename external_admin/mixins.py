from rest_framework.permissions import IsAuthenticated

from users.permissions import IsDirectorPermission


class DirectorViewMixin:
    # permission_classes = (permissions.IsAuthenticated, IsDirectorPermission,)
    pass


class StaffViewMixin:
    # permission_classes = (permissions.IsAuthenticated, IsStaffUser,)
    pass
