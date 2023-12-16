from rest_framework import permissions

from users.permissions import IsDirector, IsStaffUser


class DirectorViewMixin:
    permission_classes = (permissions.IsAuthenticated, IsDirector,)


class StaffViewMixin:
    permission_classes = (permissions.IsAuthenticated, IsStaffUser,)
