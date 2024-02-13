import logging
import time
from datetime import datetime
from functools import lru_cache
from typing import Any
import hashlib
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils.timezone import now

from service.clients.moneta import MonetaAPI
from service.clients.paybox import PayboxAPI
from service.models import Currencies
from service.utils import get_currency_by_id, get_currencies_price_per, convert_price

from .models import DeliveryAddress, OrderConversion, Customer, PaymentTransactionReceipt, Order, MonetaInvoice


def get_order(order_id):
    for _ in range(3):
        try:
            order = Order.objects.get(id=order_id)
        except ObjectDoesNotExist:
            time.sleep(1)
        else:
            return order


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


def get_receipt_moneta_price(receipt):
    if receipt.site_currency == Currencies.moneta:
        return receipt.total_price

    price_per = order_currencies_price_per(
        receipt.order_id,
        currency_from=receipt.site_currency,
        currency_to=Currencies.moneta
    )
    if price_per:
        return convert_price(receipt.total_price, price_per)


def real_receipt_usd_price(receipt):
    if receipt.site_currency == Currencies.usd:
        return receipt.total_price

    price_per = get_currencies_price_per(
        currency_from=receipt.site_currency,
        currency_to=Currencies.usd
    )
    if price_per:
        return convert_price(receipt.total_price, price_per)


def real_receipt_moneta_price(receipt):
    if receipt.site_currency == Currencies.moneta:
        return receipt.total_price

    price_per = get_currencies_price_per(
        currency_from=receipt.site_currency,
        currency_to=Currencies.moneta
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


def init_paybox_transaction(order_id, amount, transaction_uuid) -> dict[str, str]:
    payment_client = PayboxAPI(
        merchant_id=settings.PAYBOX_ID,
        secret_key=settings.PAYBOX_SECRET_KEY
    )
    response_data = payment_client.init_transaction(
        order_id=order_id,
        amount=amount,
        description="Payment for order No.%s via Paybox" % order_id,
        currency="USD",
        transaction_uuid=str(transaction_uuid),
        salt=settings.PAYBOX_SALT,
        result_url=settings.PAYBOX_RESULT_URL,
        success_url=settings.PAYBOX_SUCCESS_URL,
        failure_url=settings.PAYBOX_FAILURE_URL
    )['response']
    payment_client.session.close()
    return {
        "payment_id": response_data['pg_payment_id'],
        "redirect_url": response_data['pg_redirect_url']
    }


def is_success_transaction(transaction: PaymentTransactionReceipt) -> bool:
    payment_client = PayboxAPI(settings.PAYBOX_ID, secret_key=settings.PAYBOX_SECRET_KEY)

    try:
        response_data = payment_client.get_transaction_status(
            payment_id=str(transaction.payment_id),
            order_id=str(getattr(transaction, 'order_id')),
            salt=settings.PAYBOX_SALT
        )
    except Exception as e:
        logging.error("Paybox status error: %s" % e)
        return False
    else:
        return response_data.get("response", {}).get("pg_status", "") == "ok"


def init_moneta_invoice(order, title: str, amount: int | float) -> MonetaInvoice:
    client = MonetaAPI(merchant_id=settings.MONETA_MERCHANT_ID, private_key=settings.MONETA_PRIVATE_KEY)
    data = client.invoice(amount=amount, meta={"title": title})
    result = data.get("result", {})

    return MonetaInvoice.objects.create(
        order=order,
        invoice_id=result["invoice_id"],
        address=result["address"],
        signer=result["signer"],
        currency=result["currency"],
        amount=result["amount"],
        expired=datetime.strptime(result["expiredBy"], "%Y-%m-%d %H:%M:%S"),
        payment_link=result["paymentLink"]
    )


def get_invoice_status(invoice: MonetaInvoice) -> str:
    client = MonetaAPI(merchant_id=settings.MONETA_MERCHANT_ID, private_key=settings.MONETA_PRIVATE_KEY)
    data = client.status(invoice.invoice_id)
    return data.get("result", {}).get("status", "")

