import os
import time
from functools import lru_cache
from typing import Any
import hashlib
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils.timezone import now

from service.models import Currencies
from service.utils import get_currency_by_id, get_currencies_price_per, convert_price, generate_qrcode

from .models import DeliveryAddress, OrderConversion, Customer, Order


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


def get_bayer_code(user):
    name = user.full_name or user.email
    return f"{''.join([i[0].title() for i in name.split()])}{user.id}"


def create_customer(user):
    customer, created = Customer.objects.get_or_create(email=user.email)
    if created:
        customer.name = user.full_name
        customer.bayer_code = get_bayer_code(user)
        customer.save()
    return customer


def qrcode_for_url(filename: str, url: str):
    png = f'{filename}.png'
    directory = settings.MEDIA_ROOT / 'qrcodes'
    if not os.path.exists(directory):
        os.mkdir(directory)

    generate_qrcode(directory / png, url=url)
    return f'qrcodes/{png}'
