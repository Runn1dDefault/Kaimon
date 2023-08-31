from rest_framework.permissions import BasePermission

from order.models import Order


class OrderPermission(BasePermission):
    UPDATE_STATUSES = [Order.Status.pending]
    DELETE_STATUSES = [Order.Status.pending, Order.Status.canceled, Order.Status.rejected]

    def has_object_permission(self, request, view, obj):
        if request.METHOD in ['PUT', 'PATCH'] and obj.status not in self.UPDATE_STATUSES:
            return False
        elif request.METHOD == 'DELETE' and obj.status not in self.DELETE_STATUSES:
            return False
        return obj.delivery_address.user == request.user
