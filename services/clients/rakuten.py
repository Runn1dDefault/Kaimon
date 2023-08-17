from json import JSONDecodeError
from typing import Any

from requests import Request, Response, HTTPError

from services.clients.base import BaseClient
from services.clients.types import ProductSort


class RakutenClient(BaseClient):
    RETRIES = 3
    DELAY = 0.1
    ERROR_STATUSES = [400, 404, 429, 500, 503]
    RETRIES_STATUSES = []
    BASE_URL = "https://app.rakuten.co.jp/"
    PRODUCT_SEARCH_PATH = "/services/api/Product/Search/20170426"
    GENRE_SEARCH_PATH = "services/api/IchibaGenre/Search/20120723"

    def __init__(self, app_id: str, partner_id: str = None, **kwargs):
        self.app_id = app_id
        self.partner_id = partner_id
        super().__init__(**kwargs)

    def _setup_session(self):
        super()._setup_session()
        self.session.headers.update({'Content-Type': "application/json"})

    def process_request(self, request: Request) -> None:
        request.params['applicationId'] = self.app_id
        if self.partner_id:
            request.params['affiliateId'] = self.partner_id
        return super().process_request(request)

    def process_response(self, response: Response):
        if response.status_code in self.ERROR_STATUSES:
            raise HTTPError(
                "Status: %s\nBody: %s\nURL:%s" % (
                    response.status_code,
                    response.text,
                    response.request.url
                )
            )

        try:
            return response.json()
        except (JSONDecodeError, ValueError):
            response.raise_for_status()
            raise

    def product_search(
        self,
        keyword: str = None,
        genre_id: str = None,
        product_id: str = None,
        hits_qty: int = None,
        sort_by: ProductSort = ProductSort.standard,
        genre_info_flag: int = 1,
        or_flag: int = 0,
        min_price: int = None,
        max_price: int = None,
        page: int = None
    ) -> dict[str, Any]:
        assert keyword or genre_id or product_id
        assert genre_info_flag in [0, 1]
        assert or_flag in [0, 1]

        params = dict(
            formatVersion=2,
            sort=sort_by.value,
            genreInformationFlag=genre_info_flag,
            orFlag=or_flag
        )
        if keyword:
            params['keyword'] = keyword
        if genre_id:
            params['genreId'] = genre_id
        if product_id:
            params['productId'] = product_id
        if isinstance(hits_qty, int):
            assert 0 <= hits_qty < 30
            params['hits'] = hits_qty
        if isinstance(min_price, int):
            params['minPrice'] = min_price
        if isinstance(max_price, int):
            params['maxPrice'] = max_price
        if isinstance(page, int):
            params['page'] = page

        return self.get(self.PRODUCT_SEARCH_PATH, params)

    def genres_search(self, genre_id: int = 0):
        return self.get(self.GENRE_SEARCH_PATH, dict(formatVersion=2, genreId=genre_id))

    # def collect_all_products(self, **search_params) -> list[dict[str, Any]]:
    #     search_params.pop('page', None)
    #     first_page_data = self.product_search(**search_params)
    #     collected_products = first_page_data.get('Products', [])
    #     pages_count = first_page_data.get('pageCount', 1)
    #     for page in range(2, pages_count + 1):
    #         time.sleep(self.DELAY)
    #         search_params['page'] = page
    #         resp_data = self.product_search(**search_params)
    #         collected_products.extend(resp_data.get('Products', []))
    #     return collected_products
    #
    # collected_genres = []
    #
    # def collect_last_genres(self, genre_data: dict):
    #     time.sleep(self.DELAY)
    #     genre_id = genre_data['genreId']
    #     genre_detail = self.genres_search(genre_id)
    #     children = genre_detail.get('children', [])
    #     if not children:
    #         self.collected_genres.append(genre_data)
    #         return
    #
    #     for child in children:
    #         self.collect_last_genres(child)


if __name__ == '__main__':
    from pprint import pprint

    # Count of last categories: 13913
    rakuten = RakutenClient(app_id='1027393930619954222')
    data = rakuten.product_search(genre_id="110729", keyword="クールーネックティアードTシャツマキシワンピ")
    pprint(data)

