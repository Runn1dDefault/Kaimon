from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.http import HttpResponseNotFound
from django.shortcuts import get_object_or_404, render
from rest_framework import viewsets, generics, mixins, parsers, permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from products.serializers import ShortProductSerializer
from service.filters import ListFilter
from service.mixins import CurrencyMixin
from service.models import Currencies
from service.paginations import PagePagination
from service.utils import convert_price
from users.permissions import RegistrationPayedPermission, EmailConfirmedPermission
from users.utils import get_sentinel_user

from .models import DeliveryAddress, Order
from .permissions import OrderPermission
from .serializers import DeliveryAddressSerializer, OrderSerializer, FedexQuoteRateSerializer
from .utils import order_currencies_price_per


class DeliveryAddressViewSet(viewsets.ModelViewSet):
    queryset = DeliveryAddress.objects.all()
    permission_classes = (IsAuthenticated, EmailConfirmedPermission, RegistrationPayedPermission)
    serializer_class = DeliveryAddressSerializer
    pagination_class = PagePagination

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

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


def order_info(request, order_id):
    if request.method != 'GET':
        return HttpResponseNotFound()

    shipping_code = request.GET.get('shipping_code')
    if not shipping_code:
        return HttpResponseNotFound()

    order = get_object_or_404(Order, pk=order_id)
    try:
        shipping_detail = order.shipping_detail
    except ObjectDoesNotExist:
        return HttpResponseNotFound()

    if shipping_code != shipping_detail.shipping_code:
        return HttpResponseNotFound()

    purchased_products = []
    total_price = 0

    for receipt in order.receipts.all():
        price = receipt.total_price
        unit_price = receipt.unit_price

        if receipt.site_currency != Currencies.yen:
            price_per = order_currencies_price_per(
                order_id=receipt.order_id,
                currency_from=receipt.site_currency,
                currency_to=Currencies.yen
            )
            price = convert_price(price, price_per) if price_per else 0.0
            unit_price = convert_price(unit_price, price_per) if price_per else 0.0

        total_price += float(price)
        purchased_products.append(
            {
                "code": receipt.product_code,
                "url": receipt.product_url,
                "product_name": receipt.product_name,
                "quantity": receipt.quantity,
                "unit_price": round(unit_price, 2),
                "original_price": round(receipt.site_price, 2),
                "currency": Currencies.to_symbol(receipt.site_currency),
                "total": round(price, 2),
                "tags": receipt.tags
            }
        )
    return render(
        request,
        "order_check.html",
        context={
            "order": {
                "buyer": order.customer.name,
                "buyer_code": order.bayer_code,
                "purchase_date": order.created_at.date(),
                "total_order_amount": round(total_price, 2)
            },
            "purchased_products": purchased_products,
            "currency": "¥"
        }
    )
