from rest_framework.permissions import BasePermission

from order.models import Order


class AuthorPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user.is_authenticated and request.user == obj.user


class OrderPermission(BasePermission):
    DELETE_STATUSES = [Order.Status.pending, Order.Status.rejected, Order.Status.canceled]

    def has_object_permission(self, request, view, obj):
        if obj.delivery_address.user != request.user:
            return False
        if request.method == 'DELETE' and obj.status not in self.DELETE_STATUSES:
            return False
        return True
