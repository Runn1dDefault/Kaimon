from rest_framework import permissions

from users.permissions import IsDirectorPermission, IsStaffUser


class DirectorViewMixin:
    permission_classes = (permissions.IsAuthenticated, IsDirectorPermission,)


class StaffViewMixin:
    permission_classes = (permissions.IsAuthenticated, IsStaffUser,)
