import random

import numpy as np
from typing import Any

from rakuten_scraping.models import Oauth2Client
from services.clients import RakutenClient


def get_rakuten_client(delay: int | float, validation_client: bool = False) -> RakutenClient:
    db_client = Oauth2Client.cached_objects.free_client(validation_client)
    rakuten_client = RakutenClient(
        app_id=db_client.app_id,
        partner_id=db_client.partner_id or None
    )
    Oauth2Client.cached_objects.set_busy(
        client_id=db_client.id,
        app_id=db_client.app_id,
        # with a random downtime method there is less chance of ban
        delay=random.choice(list(np.arange(delay, delay * 1.5, 0.1)))
    )
    return rakuten_client


def build_by_fields_map(data: dict[str, Any], fields_map: dict[str, str]):
    query = {}
    for db_field, rakuten_field in fields_map.items():
        query[db_field] = data[rakuten_field]
    return query
