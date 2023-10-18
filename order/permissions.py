from rest_framework.permissions import BasePermission

from order.models import Order


class OrderPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        user_has_perm = self.has_obj_perm(request, obj)
        if request.method == 'DELETE':
            return user_has_perm and self.has_perm_to_delete(obj)
        elif request.method in ('PUT', 'PATCH'):
            return user_has_perm and self.has_perm_to_update(obj)
        return user_has_perm

    @staticmethod
    def has_obj_perm(request, obj):
        return obj.delivery_address.user == request.user or request.user.is_superuser

    @staticmethod
    def has_perm_to_delete(obj):
        return obj.status in Order.Status.delete_statuses()

    @staticmethod
    def has_perm_to_update(obj):
        return obj.status in Order.Status.update_statuses()
