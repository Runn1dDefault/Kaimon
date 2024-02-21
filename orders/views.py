from copy import deepcopy

import xmltodict
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.http import HttpResponseNotFound
from django.shortcuts import get_object_or_404, render
from drf_spectacular.utils import extend_schema
from rest_framework import views, viewsets, generics, mixins, parsers, permissions, status
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from service.filters import ListFilter
from service.mixins import CurrencyMixin
from service.models import Currencies
from service.paginations import PagePagination
from service.utils import convert_price
from users.permissions import RegistrationPayedPermission, EmailConfirmedPermission
from users.utils import get_sentinel_user

from .models import DeliveryAddress, Order, Payment
from .permissions import OrderPermission
from .serializers import DeliveryAddressSerializer, OrderSerializer, FedexQuoteRateSerializer
from .utils import order_currencies_price_per


class DeliveryAddressViewSet(viewsets.ModelViewSet):
    queryset = DeliveryAddress.objects.filter(as_deleted=False)
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
    permission_classes = (IsAuthenticated, EmailConfirmedPermission, RegistrationPayedPermission, OrderPermission)
    parser_classes = (parsers.JSONParser,)
    pagination_class = PagePagination
    filter_backends = (ListFilter, OrderingFilter)
    ordering_fields = ("created_at",)
    list_filter_fields = {'status': 'status'}

    @extend_schema(parameters=[settings.CURRENCY_QUERY_SCHEMA_PARAM])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

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


class PayboxResultView(views.APIView):
    queryset = Payment.objects.filter(payment_type=Payment.PaymentType.paybox)
    MESSAGES = {
        "empty": {'pg_status': 'error', 'pg_description': ''},
        "interpretation": {'pg_status': 'error','pg_description': 'Ошибка в интерпретации данных'},
        "rejected": {'pg_status': 'rejected', 'pg_description': 'Ожидание успешного статуса оплаты'},
        "success": {'pg_status': 'ok', 'pg_description': 'Заказ оплачен'}
    }

    def _xml_response(self, key: str, sig=None, salt=None, **kwargs) -> Response:
        resp_data = deepcopy(self.MESSAGES[key])
        if sig:
            resp_data["pg_sig"] = sig
        if salt:
            resp_data["pg_salt"] = salt
        return Response(xmltodict.unparse({"response": resp_data}), **kwargs)

    def post(self, request):
        payload = request.data or {}
        salt = payload.get("pg_salt")
        signature = payload.get("pg_sig")

        if not salt or salt != settings.PAYBOX_SALT or not signature:
            return self._xml_response("empty", status=status.HTTP_403_FORBIDDEN)

        payment_id, payment_status = payload.get('pg_payment_id'), payload.get("pg_result", "")
        if (
            not payment_id
            or not self.queryset.filter(payment_id=payment_id).exists()
            or payment_status not in ("0", "1")
        ):
            return self._xml_response("interpretation", salt=salt, sig=signature,
                                      status=status.HTTP_400_BAD_REQUEST)

        payment = self.queryset.filter(payment_id=payment_id).first()
        order = payment.order
        if payment_status == "0":
            order.status = Order.Status.payment_rejected
            order.save()
            return self._xml_response("rejected", sig=signature, salt=salt)

        payment.payment_meta = payload
        payment.save()
        order.status = Order.Status.pending
        order.save()
        return self._xml_response("success", sig=signature, salt=salt)
