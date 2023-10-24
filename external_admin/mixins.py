from rest_framework import permissions

from users.permissions import IsDirectorPermission, IsStaffUser


class DirectorViewMixin:
    pass
    # permission_classes = (permissions.IsAuthenticated, IsDirectorPermission,)


class StaffViewMixin:
    pass
    # permission_classes = (permissions.IsAuthenticated, IsStaffUser,)
