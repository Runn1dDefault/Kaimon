import random
import time

import numpy as np
from typing import Any

from rakuten_scraping.models import Oauth2Client
from utils.clients.rakuten import RakutenClient


class RakutenRequest:
    def __init__(self, delay: int = None, randomize_delay: bool = True):
        self.randomize_delay = randomize_delay
        self.delay = delay
        self.db_client = Oauth2Client.objects.free_client()
        self.client = RakutenClient(app_id=self.db_client.app_id, partner_id=self.db_client.partner_id or None)

    def close(self):
        st = time.monotonic()
        time.sleep(self._get_delay())
        print(f'Set Free {time.monotonic() - st}')
        Oauth2Client.objects.set_free(self.db_client.id, self.db_client.app_id)

    def _random_delay(self) -> float:
        return random.choice(list(np.arange(self.delay, self.delay * 1.5, 0.1)))

    def _get_delay(self) -> float:
        if self.delay and self.randomize_delay:
            rand_delay = self._random_delay()
            print('Random Delay is %s' % rand_delay)
            return rand_delay
        return self.delay

    def __enter__(self):
        Oauth2Client.objects.set_busy(
            client_id=self.db_client.id,
            app_id=self.db_client.app_id
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def build_genre_fields(data: dict[str, Any], fields: dict[str, str]):
    query = {}
    for db_field, rakuten_field in fields.items():
        query[db_field] = data[rakuten_field]
    return query


def build_product_fields(item: dict[str, Any]):
    return dict(
        id=item['itemCode'],
        name=item['itemName'],
        description=item['itemCaption'],
        price=item['itemPrice'],
        product_url=item['itemUrl'],
        availability=True if item['availability'] == 1 else False
    )
