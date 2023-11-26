from functools import lru_cache
from typing import Any
import hashlib
from uuid import uuid4

from django.utils.timezone import now

from service.models import Currencies
from service.utils import get_currency_by_id, get_currencies_price_per, convert_price

from .models import DeliveryAddress, OrderConversion, Customer


def duplicate_delivery_address(delivery_address, updates: dict[str, Any]):
    new_address = DeliveryAddress(
        user=delivery_address.user,
        recipient_name=delivery_address.recipient_name,
        address_line=delivery_address.address_line,
        city=delivery_address.city,
        state=delivery_address.state,
        postal_code=delivery_address.postal_code,
        country=delivery_address.country
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
    conversion = OrderConversion.objects.filter(order_id=order_id, currency_from=currency_from, currency_to=currency_to)
    if conversion:
        return conversion.price_per


def create_customer(user, phone):
    name = user.full_name or user.email
    bayer_code = f"{''.join([i[0].title() for i in name.split()])}{Customer.objects.count() + 1}"
    customer, _ = Customer.objects.get_or_create(
        name=user.full_name,
        bayer_code=bayer_code,
        email=user.email,
        phone=phone
    )
    return customer
