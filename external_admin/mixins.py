from rest_framework import permissions

from users.permissions import IsDirector, IsStaffUser


class DirectorViewMixin:
    pass
    # permission_classes = (permissions.IsAuthenticated, IsDirector,)


class StaffViewMixin:
    pass
    # permission_classes = (permissions.IsAuthenticated, IsStaffUser,)
