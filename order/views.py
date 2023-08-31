from rest_framework import generics, viewsets

from users.filters import FilterByUser
from users.permissions import RegistrationPayedPermission
from utils.mixins import LanguageMixin
from utils.filters import FilterByFields
from utils.paginators import PagePagination

from .models import Country, UserDeliveryAddress, Order
from .permissions import OrderPermission
from .serializers import CountrySerializer, DeliveryAddressSerializer, OrderSerializer


class CountryListView(LanguageMixin, generics.ListAPIView):
    queryset = Country.objects.filter(is_active=True)
    serializer_class = CountrySerializer
    permission_classes = [RegistrationPayedPermission]


class DeliveryAddressViewSet(LanguageMixin, viewsets.ModelViewSet):
    queryset = UserDeliveryAddress.objects.filter(is_deleted=False)
    permission_classes = [RegistrationPayedPermission]
    serializer_class = DeliveryAddressSerializer
    pagination_class = PagePagination
    filter_backends = [FilterByUser]
    user_relation_field = 'delivery_addresses'
    user_relation_filters = {'is_deleted': False}

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save()


class OrderViewSet(LanguageMixin, viewsets.ModelViewSet):
    queryset = Order.objects.filter(is_deleted=False)
    permission_classes = [RegistrationPayedPermission, OrderPermission]
    serializer_class = OrderSerializer
    pagination_class = PagePagination
    filter_backends = [FilterByFields]
    filter_fields = {'status': {'db_field': 'status', 'type': 'enum', 'choices': Order.Status.choices}}

    def get_queryset(self):
        return super().get_queryset()

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.delete_receipts()
        instance.save()
