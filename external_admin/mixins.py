from rest_framework import permissions

from order.models import Order
from promotions.models import Promotion
from users.models import User
from users.permissions import IsDirectorPermission

from .paginators import UserListPagination
from .serializers import AdminUserSerializer, AdminOrderSerializer


class UserAdminViewMixin:
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser,)
    pagination_class = UserListPagination
    queryset = User.objects.filter(role__in=[User.Role.CLIENT])
    serializer_class = AdminUserSerializer


class OrderAdminViewMixin:
    queryset = Order.objects.all()
    serializer_class = AdminOrderSerializer
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser)


class PromotionAdminViewMixin:
    queryset = Promotion.objects.all()
    lookup_field = 'id'
    permission_classes = [permissions.IsAuthenticated, IsDirectorPermission]
