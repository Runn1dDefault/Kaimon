from json import JSONDecodeError
from typing import Any

from requests import Request, Response, HTTPError

from services.clients.base import BaseClient
from services.clients.types import ProductSort, ItemSort


class RakutenClient(BaseClient):
    RETRIES = 3
    DELAY = 0.1
    ERROR_STATUSES = [400, 404, 429, 500, 503]
    RETRIES_STATUSES = []
    BASE_URL = "https://app.rakuten.co.jp/"
    PRODUCT_SEARCH_PATH = "/services/api/Product/Search/20170426"
    GENRE_SEARCH_PATH = "services/api/IchibaGenre/Search/20120723"
    ITEM_SEARCH_PATH = "/services/api/IchibaItem/Search/20220601"
    TAG_SEARCH_PATH = "/services/api/IchibaTag/Search/20140222"

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
        genre_id: str | int = None,
        product_id: str | int = None,
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

        if product_id:
            return self.get(self.PRODUCT_SEARCH_PATH, {'productId': product_id})

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

    def tag_search(self, tag_id: int | str):
        params = dict(tagId=tag_id, formatVersion=2)
        return self.get(self.TAG_SEARCH_PATH, params)

    def item_search(
        self,
        keyword: str = None,
        shop_code: str = None,
        item_code: str = None,
        genre_id: int | str = None,
        tag_id: int | str = None,
        hits_qty: int = None,
        sort_by: ItemSort = ItemSort.standard,
        with_genre_info: bool = True,
        with_tags_info: bool = True,
        has_movie: bool = False,
        has_pamphlets: bool = False,
        appoint_delivery_date: bool = False,
        min_price: int = None,
        max_price: int = None,
        page: int = None,
        exclude_keyword: str = None,
        output_elements: str = None
    ):
        params = dict(
            formatVersion=2,
            imageFlag=1,
            availability=1,
            sort=sort_by.value,
            genreInformationFlag=1 if with_genre_info is True else 0,
            tagInformationFlag=1 if with_tags_info is True else 0,
            hasMovieFlag=1 if has_movie is True else 0,
            pamphletFlag=1 if has_pamphlets is True else 0,
            appointDeliveryDateFlag=1 if appoint_delivery_date is True else 0,
        )
        if keyword:
            params['keyword'] = keyword
        if shop_code:
            params['shopCode'] = shop_code
        if item_code:
            params['itemCode'] = item_code
        if genre_id:
            params['genreId'] = genre_id
        if tag_id:
            params['tagId'] = tag_id
        if output_elements:
            params['elements'] = output_elements

        if isinstance(hits_qty, int):
            assert 0 <= hits_qty < 30
            params['hits'] = hits_qty
        if isinstance(min_price, int):
            params['minPrice'] = min_price
        if isinstance(max_price, int):
            params['maxPrice'] = max_price
        if isinstance(page, int):
            params['page'] = page
        if exclude_keyword:
            params['NGKeyword'] = exclude_keyword
        return self.get(self.ITEM_SEARCH_PATH, params)


if __name__ == '__main__':
    from pprint import pprint

    # Count of last categories: 13913
    rakuten = RakutenClient(app_id='1027393930619954222')
    # pprint(rakuten.genres_search())
    # pprint(rakuten.item_search(genre_id=568674))
    # pprint(rakuten.product_search(keyword='フロントップ楽天市場店'))
    # pprint(rakuten.tag_search(1000319))

    # data = rakuten.product_search(genre_id=568674)
    data = rakuten.item_search(item_code="thematerialworld:10016878")
    pprint(data)
