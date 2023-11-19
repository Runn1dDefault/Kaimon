from django.db import transaction
from rest_framework import viewsets, generics, mixins, parsers, permissions
from rest_framework.response import Response

from currencies.mixins import CurrencyMixin
from product.serializers import ProductListSerializer
from users.filters import FilterByUser
from users.permissions import RegistrationPayedPermission, EmailConfirmedPermission
from utils.filters import ListFilter
from utils.paginators import PagePagination

from .models import DeliveryAddress, Order
from .permissions import OrderPermission
from .serializers import DeliveryAddressSerializer, OrderSerializer, FedexQuoteRateSerializer


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
    filter_backends = [ListFilter]
    list_filter_fields = {'status': 'status'}

    def perform_create(self, serializer):
        with transaction.atomic():
            super().perform_create(serializer)

    def get_queryset(self):
        return super().get_queryset().filter(delivery_address__user=self.request.user)


class FedexQuoteRateView(generics.GenericAPIView):
    authentication_classes = ()
    permission_classes = (permissions.AllowAny,)
    parser_classes = (parsers.JSONParser,)
    serializer_class = FedexQuoteRateSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(data=serializer.data)
