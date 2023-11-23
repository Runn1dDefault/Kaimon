from typing import Any
import hashlib
from uuid import uuid4

from django.conf import settings
from django.utils import timezone
from django.utils.timezone import now

from products.models import Product
from service.clients import fedex
from .models import DeliveryAddress


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


def fedex_international_quotes(
    products_with_count: list[dict[str, Product | int]],
    country_code: str,
    postal_code: str = None,
    city: str = None
):
    commodities = []
    for data in products_with_count:
        genre = data['product'].genres.filter(avg_weight__isnull=False).first()
        if not genre:
            # TODO: add logic if all genres of product does not have a avg_weight
            continue

        commodities.append(
            fedex.FedexCommodity(
                weight=fedex.FedexWeight(units='KG', value=genre.avg_weight),
                currency_amount=fedex.FedexCurrencyAmount(currency="JYE", amount=100),
                desciption=genre.fedex_description,
                quantity=data['quantity'],
                quantity_units="PCS"
            )
        )

    client = fedex.FedexAPIClient(
        client_id=settings.FEDEX_CLIENT_ID,
        client_secret=settings.FEDEX_SECRET,
        account_number=settings.FEDEX_ACCOUNT_NUMBER,
        use_test=True  # TODO: change settings and delete this param on prod
    )
    return client.international_rate_quotes(
        shipper=fedex.FedexAddress(
            postal_code=settings.SHIPPER_POSTAL_CODE,
            country_code=settings.SHIPPER_COUNTRY_CODE
        ),
        recipient=fedex.FedexAddress(
            country_code=country_code,
            city=city,
            postal_code=postal_code
        ),
        pickup_type=fedex.FedexPickupType.CONTACT_FEDEX_TO_SCHEDULE,
        commodities=commodities,
        ship_date=(timezone.localtime(timezone.now()) + timezone.timedelta(days=3)).date()
    )
