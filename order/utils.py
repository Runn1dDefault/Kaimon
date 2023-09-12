from typing import Any

from .models import DeliveryAddress


def duplicate_delivery_address(delivery_address, updates: dict[str, Any]):
    new_address = DeliveryAddress(
        recipient_name=delivery_address.recipient_name,
        address_line1=delivery_address.address_line1,
        address_line2=delivery_address.address_line2,
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

