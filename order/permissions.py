from rest_framework.permissions import BasePermission

from order.models import Order


class OrderPermission(BasePermission):
    DELETE_STATUSES = [Order.Status.pending, Order.Status.success]

    def has_object_permission(self, request, view, obj):
        if request.METHOD in ['PUT', 'PATCH', 'DELETE'] and obj.status not in self.DELETE_STATUSES:
            return False
        return obj.delivery_address.user == request.user
