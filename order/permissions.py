from rest_framework.permissions import BasePermission

from order.models import Order


class AuthorPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user.is_authenticated and request.user == obj.user


class OrderPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        if obj.delivery_address.user != request.user:
            return False
        return True
