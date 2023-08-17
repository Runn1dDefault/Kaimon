from typing import Any

from product.models import Genre
from rakuten_scraping.models import Oauth2Client
from services.clients.rakuten import RakutenClient


class RakutenRequest:
    def __init__(self):
        self.db_client = Oauth2Client.objects.free_client()
        self.client = RakutenClient(app_id=self.db_client.app_id, partner_id=self.db_client.partner_id or None)

    def close(self):
        self.db_client.set_free()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def get_db_genre_by_data(data: dict[str, Any], fields: dict[str, str]):
    query = {}
    for db_field, rakuten_field in fields.items():
        query[db_field] = data[rakuten_field]

    return Genre(**query)

