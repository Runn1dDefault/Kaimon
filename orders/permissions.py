from rest_framework.permissions import BasePermission


class OrderPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        user_has_perm = obj.delivery_address.user == request.user or request.user.is_staff
        if request.method == 'DELETE':
            return user_has_perm and obj.status == obj.Status.wait_payment
        return user_has_perm
