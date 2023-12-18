from decimal import Decimal
from pprint import pprint

import xmltodict
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.http import HttpResponseNotFound
from django.shortcuts import get_object_or_404, render
from drf_spectacular.utils import extend_schema
from rest_framework import views, viewsets, generics, mixins, parsers, permissions, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from service.filters import ListFilter
from service.mixins import CurrencyMixin
from service.models import Currencies
from service.paginations import PagePagination
from service.utils import convert_price
from users.permissions import RegistrationPayedPermission, EmailConfirmedPermission
from users.utils import get_sentinel_user

from .models import DeliveryAddress, Order, PaymentTransactionReceipt
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
    filter_backends = (ListFilter,)
    list_filter_fields = {'status': 'status'}

    @extend_schema(parameters=[settings.CURRENCY_QUERY_SCHEMA_PARAM])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

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


class PayboxResultView(views.APIView):
    transaction_receipt_model = PaymentTransactionReceipt

    def post(self, request):
        payload = request.data
        salt = payload.get("pg_salt")
        signature = payload.get("pg_sig")

        if not salt or salt != settings.PAYBOX_SALT or not signature:
            return Response(
                xmltodict.unparse(
                    {
                        'response': {
                            'pg_status': 'error',
                            'pg_description': ''
                        }
                    }
                ),
                status=status.HTTP_403_FORBIDDEN
            )

        payment_id = payload.get('pg_payment_id')
        payment_status = payload.get("pg_result", "")
        can_reject = payload.get("pg_can_reject", "")

        if (
            not payment_id
            or not self.transaction_receipt_model.objects.filter(payment_id=payment_id).exists()
            or payment_status not in ("0", "1")
            or can_reject not in ("0", "1")
        ):
            return Response(
                xmltodict.unparse(
                    {
                        'response': {
                            'pg_status': 'error',
                            'pg_description': 'Ошибка в интерпретации данных',
                            'pg_salt': salt,
                            'pg_sig': signature
                        }
                    }
                ),
                status=status.HTTP_400_BAD_REQUEST
            )

        receipt = self.transaction_receipt_model.objects.filter(payment_id=payment_id).first()
        transaction_uuid = payload.get("transaction_uuid", "")

        if transaction_uuid != str(receipt.uuid):
            return Response(
                xmltodict.unparse(
                    {
                        'response': {
                            'pg_status': 'error',
                            'pg_description': 'Ошибка в интерпретации данных',
                            'pg_salt': salt,
                            'pg_sig': signature
                        }
                    }
                ),
                status=status.HTTP_400_BAD_REQUEST
            )

        order = receipt.order
        if payment_status == "0":
            order.status = Order.Status.payment_rejected
            order.save()
            return Response(
                xmltodict.unparse(
                    {
                        'response': {
                            'pg_status': 'rejected',
                            'pg_description': 'Ожидание успешного статуса оплаты',
                            'pg_salt': salt,
                            'pg_sig': signature
                        }
                    }
                ),
                status=status.HTTP_200_OK
            )

        payment_receipt = get_object_or_404(self.transaction_receipt_model, payment_id=payment_id)
        payment_receipt.receive_amount = payload.get("pg_amount")
        payment_receipt.receive_currency = payload.get("pg_currency")
        payment_receipt.clearing_amount = Decimal(payload.get("pg_clearing_amount", 0))
        payment_receipt.card_name = payload.get("pg_card_name")
        payment_receipt.card_pan = payload.get("card_pan")
        payment_receipt.auth_code = payload.get("auth_code")
        payment_receipt.reference = payload.get("pg_reference")
        payment_receipt.payment_status = payment_status
        payment_receipt.save()
        order.status = Order.Status.pending
        order.save()
        return Response(
            xmltodict.unparse(
                {
                    'response': {
                        'pg_status': 'ok',
                        'pg_description': 'Заказ оплачен',
                        'pg_salt': salt,
                        'pg_sig': signature
                    }
                }
            ),
            status=status.HTTP_200_OK
        )
