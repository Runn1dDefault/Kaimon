from rest_framework.permissions import BasePermission


class OrderPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        user_has_perm = obj.delivery_address.user == request.user or request.user.is_superuser
        if request.method == 'DELETE':
            return user_has_perm and obj.status == obj.status.pending
        return user_has_perm
