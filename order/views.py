from django.db import transaction
from rest_framework import viewsets, mixins, parsers

from currencies.mixins import CurrencyMixin
from product.serializers import ProductListSerializer
from users.filters import FilterByUser
from users.permissions import RegistrationPayedPermission, EmailConfirmedPermission
from utils.filters import ListFilterFields
from utils.paginators import PagePagination

from .models import DeliveryAddress, Order
from .permissions import OrderPermission
from .serializers import DeliveryAddressSerializer, OrderSerializer


class DeliveryAddressViewSet(viewsets.ModelViewSet):
    queryset = DeliveryAddress.objects.filter(as_deleted=False)
    permission_classes = [EmailConfirmedPermission, RegistrationPayedPermission]
    serializer_class = DeliveryAddressSerializer
    pagination_class = PagePagination
    filter_backends = [FilterByUser]
    user_relation_field = 'delivery_addresses'
    user_relation_filters = {'as_deleted': False}

    def perform_destroy(self, instance):
        if instance.orders.exists():
            instance.as_deleted = True
            instance.save()
        else:
            instance.delete()


class OrderViewSet(
    CurrencyMixin,
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet
):
    queryset = Order.objects.all()
    parser_classes = (parsers.JSONParser,)
    permission_classes = [EmailConfirmedPermission, RegistrationPayedPermission, OrderPermission]
    serializer_class = OrderSerializer
    product_serializer_class = ProductListSerializer
    pagination_class = PagePagination
    filter_backends = [ListFilterFields]
    list_filter_fields = {'status': 'status'}

    def perform_create(self, serializer):
        with transaction.atomic():
            super().perform_create(serializer)

    def get_queryset(self):
        return super().get_queryset().filter(delivery_address__user=self.request.user)
