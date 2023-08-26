from rest_framework.permissions import BasePermission


class OrderPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.delivery_address.user == request.user
