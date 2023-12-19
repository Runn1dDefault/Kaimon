import logging
from functools import lru_cache
from typing import Any
import hashlib
from uuid import uuid4

from django.conf import settings
from django.utils.timezone import now
from rest_framework.exceptions import ValidationError

from service.clients.paybox import PayboxAPI
from service.models import Currencies
from service.utils import get_currency_by_id, get_currencies_price_per, convert_price

from .models import DeliveryAddress, OrderConversion, Customer, PaymentTransactionReceipt


def duplicate_delivery_address(delivery_address, updates: dict[str, Any]):
    new_address = DeliveryAddress(
        user=delivery_address.user,
        recipient_name=delivery_address.recipient_name,
        country_code=delivery_address.country_code,
        city=delivery_address.city,
        postal_code=delivery_address.postal_code,
        address_line=delivery_address.address_line
    )

    for field, value in updates.items():
        if hasattr(new_address, field):
            setattr(new_address, field, value)
    new_address.save()
    return new_address


def generate_shipping_code():
    sha256_hash = hashlib.sha256()
    sha256_hash.update(f"{uuid4()}{now().timestamp()}".encode('utf-8'))
    return sha256_hash.hexdigest()


@lru_cache(maxsize=50)
def get_product_yen_price(product, quantity):
    product_currency = get_currency_by_id(product.id)
    if product_currency == Currencies.yen:
        return (product.sale_price or product.price) * quantity

    price_per = get_currencies_price_per(currency_from=product_currency, currency_to=Currencies.yen)
    return convert_price(product.sale_price or product.price, price_per) * quantity


@lru_cache(maxsize=100)
def order_currencies_price_per(order_id, currency_from: str, currency_to: str):
    conversion = OrderConversion.objects.filter(
        order_id=order_id,
        currency_from=currency_from,
        currency_to=currency_to
    ).first()
    if conversion:
        return conversion.price_per


def get_receipt_usd_price(receipt):
    if receipt.site_currency == Currencies.usd:
        return receipt.total_price

    price_per = order_currencies_price_per(
        receipt.order_id,
        currency_from=receipt.site_currency,
        currency_to=Currencies.usd
    )
    if price_per:
        return convert_price(receipt.total_price, price_per)


def get_bayer_code(user):
    name = user.full_name or user.email
    return f"{''.join([i[0].title() for i in name.split()])}{user.id}"


def create_customer(user):
    customer, _ = Customer.objects.get_or_create(
        name=user.full_name,
        bayer_code=get_bayer_code(user),
        email=user.email
    )
    return customer


def init_paybox_transaction(order, amount, uuid) -> dict[str, str]:
    payment_client = PayboxAPI(settings.PAYBOX_ID, secret_key=settings.PAYBOX_SECRET_KEY)
    response_data = payment_client.init_transaction(
        order_id=order.id,
        amount=amount,
        description="Payment for order No.%s via Paybox" % order.id,
        salt=settings.PAYBOX_SALT,
        currency="USD",
        result_url=settings.PAYBOX_RESULT_URL,
        success_url=settings.PAYBOX_SUCCESS_URL,
        failure_url=settings.PAYBOX_FAILURE_URL,
        transaction_uuid=str(uuid)
    )
    data = response_data.get('response', {})
    url = data.get('pg_redirect_url')
    payment_id = data.get('payment_id')
    if not url or not payment_id:
        raise ValidationError({"detail": "Something went wrong, please try another time."})
    return {
        "payment_id": payment_id,
        "redirect_url": url
    }


def is_success_transaction(transaction: PaymentTransactionReceipt) -> bool:
    payment_client = PayboxAPI(settings.PAYBOX_ID, secret_key=settings.PAYBOX_SECRET_KEY)

    try:
        response_data = payment_client.get_transaction_status(
            payment_id=transaction.payment_id,
            order_id=getattr(transaction, 'order_id'),
            salt=settings.PAYBOX_SALT
        )
    except Exception as e:
        logging.error("Paybox status error: ", e)
        return False
    else:
        return response_data.get("response", {}).get("pg_status", "") == "ok"
