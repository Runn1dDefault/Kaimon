from rest_framework import generics, viewsets

from product.paginators import PagePagination
from users.filters import FilterByUser
from users.permissions import RegistrationPayedPermission
from utils.mixins import LanguageMixin

from .models import Country, UserDeliveryAddress, Order
from .permissions import OrderPermission
from .serializers import CountrySerializer, DeliveryAddressSerializer, OrderSerializer


# TODO: add filtering by language


class CountryListView(generics.ListAPIView, LanguageMixin):
    queryset = Country.objects.filter(is_active=True)
    serializer_class = CountrySerializer
    permission_classes = [RegistrationPayedPermission]


class DeliveryAddressViewSet(viewsets.ModelViewSet, LanguageMixin):
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


class OrderViewSet(viewsets.ModelViewSet, LanguageMixin):
    queryset = Order.objects.filter(is_deleted=False)
    permission_classes = [RegistrationPayedPermission, OrderPermission]
    serializer_class = OrderSerializer
    pagination_class = PagePagination

    def get_queryset(self):
        return super().get_queryset().filter(delivery_address__user=self.request.user)

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save()
