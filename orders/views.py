from django.db import transaction
from rest_framework import viewsets, generics, mixins, parsers, permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from products.serializers import ShortProductSerializer
from service.filters import ListFilter
from service.mixins import CurrencyMixin
from service.paginations import PagePagination
from users.permissions import RegistrationPayedPermission, EmailConfirmedPermission
from users.utils import get_sentinel_user

from .models import DeliveryAddress, Order
from .permissions import OrderPermission
from .serializers import DeliveryAddressSerializer, OrderSerializer, FedexQuoteRateSerializer


class DeliveryAddressViewSet(viewsets.ModelViewSet):
    queryset = DeliveryAddress.objects.all()
    permission_classes = (IsAuthenticated, EmailConfirmedPermission, RegistrationPayedPermission)
    serializer_class = DeliveryAddressSerializer
    pagination_class = PagePagination

    def get_queryset(self):
        return super().get_queryset().filter(delivery_addresses__user=self.request.user)

    def perform_destroy(self, instance):
        if instance.orders.exists():
            instance.user = get_sentinel_user()
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
    serializer_class = OrderSerializer
    product_serializer_class = ShortProductSerializer
    permission_classes = (IsAuthenticated, EmailConfirmedPermission, RegistrationPayedPermission, OrderPermission)
    parser_classes = (parsers.JSONParser,)
    pagination_class = PagePagination
    filter_backends = (ListFilter,)
    list_filter_fields = {'status': 'status'}

    def perform_create(self, serializer):
        with transaction.atomic():
            super().perform_create(serializer)

    def get_queryset(self):
        return super().get_queryset().filter(delivery_address__user=self.request.user)


class FedexQuoteRateView(generics.GenericAPIView):
    permission_classes = (permissions.AllowAny,)
    parser_classes = (parsers.JSONParser,)
    serializer_class = FedexQuoteRateSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(data=serializer.data)
