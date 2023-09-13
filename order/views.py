from rest_framework import viewsets, mixins
from rest_framework.decorators import action

from product.models import Product
from product.serializers import ProductListSerializer
from users.filters import FilterByUser
from users.permissions import RegistrationPayedPermission
from utils.filters import FilterByFields
from utils.paginators import PagePagination

from .models import DeliveryAddress, Order
from .permissions import OrderPermission
from .serializers import DeliveryAddressSerializer, OrderSerializer


class DeliveryAddressViewSet(viewsets.ModelViewSet):
    queryset = DeliveryAddress.objects.filter(as_deleted=False)
    permission_classes = [RegistrationPayedPermission]
    serializer_class = DeliveryAddressSerializer
    pagination_class = PagePagination
    filter_backends = [FilterByUser]
    user_relation_field = 'delivery_addresses'
    user_relation_filters = {'as_deleted': False}

    def perform_destroy(self, instance):
        instance.as_deleted = True
        instance.save()


class OrderViewSet(
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):
    queryset = Order.objects.all()
    permission_classes = [RegistrationPayedPermission, OrderPermission]
    serializer_class = OrderSerializer
    product_serializer_class = ProductListSerializer
    pagination_class = PagePagination
    filter_backends = [FilterByFields]
    filter_fields = {'status': {'db_field': 'status', 'type': 'enum', 'choices': Order.Status.choices}}

    def get_queryset(self):
        return super().get_queryset().filter(delivery_address__user=self.request.user)

    def perform_destroy(self, instance):
        instance.status = Order.Status.canceled
        instance.save()

    @action(methods=['GET'], detail=True)
    def order_products(self, request, **kwargs):
        product_ids = self.get_object().receipts.values_list('product_id', flat=True)
        products = Product.objects.filter(id__in=product_ids, is_active=True, availability=True)
        page = self.paginate_queryset(products)
        serializer = self.product_serializer_class(page, many=True, context=self.get_serializer_context())
        return self.get_paginated_response(serializer.data)
