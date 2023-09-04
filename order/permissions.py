from rest_framework.permissions import BasePermission

from order.models import Order


class OrderPermission(BasePermission):
    UPDATE_STATUSES = [Order.Status.pending]
    DELETE_STATUSES = [Order.Status.pending, Order.Status.rejected, Order.Status.canceled]

    def has_object_permission(self, request, view, obj):
        if obj.delivery_address.user != request.user:
            return False
        if request.METHOD in ['PUT', 'PATCH'] and obj.status not in self.UPDATE_STATUSES:
            return False
        if request.METHOD == 'DELETE' and obj.status not in self.DELETE_STATUSES:
            return False
        return True

