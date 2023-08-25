import random
import time
from datetime import datetime

import numpy as np
from typing import Any

from product.models import Genre
from rakuten_scraping.models import Oauth2Client
from services.clients.rakuten import RakutenClient


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


def get_db_genre_by_data(data: dict[str, Any], fields: dict[str, str]):
    query = {}
    for db_field, rakuten_field in fields.items():
        query[db_field] = data[rakuten_field]

    return Genre(**query)


def get_release_date_from_ja(ja_release_date: str):
    release_date = None
    date_format = None
    if '年' in ja_release_date and '月' in ja_release_date:
        date_format = "%Y年%m月"
    if '日' in ja_release_date:
        date_format = "%Y年%m月%d日"

    if date_format:
        release_date = datetime.strptime(ja_release_date, date_format).date()
    return release_date


def collect_product_fields(product_data: dict[str, Any]):
    image_url = product_data.get('mediumImageUrl') or product_data.get('smallImageUrl')
    release_date = get_release_date_from_ja(product_data['releaseDate'])

    return dict(
        number=product_data['productNo'],
        name=product_data['productName'],
        description=product_data['productCaption'],
        brand_name=product_data['brandName'],
        rank=product_data['rank'],
        price=product_data['maxPrice'],
        count=product_data['itemCount'],
        image_url=image_url.split('?')[0] if image_url else None,
        product_url=product_data['productUrlPC'],
        release_date=release_date,
        marker_code=product_data['makerCode'] or None
    )
