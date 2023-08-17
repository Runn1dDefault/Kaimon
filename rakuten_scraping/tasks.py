from datetime import datetime
from typing import Any

from celery import shared_task
from django.utils.dateparse import parse_date

from product.models import Genre, GenreChild, Product, ProductDetail, Marker
from rakuten_scraping.settings import app_settings
from rakuten_scraping.utils import RakutenRequest, get_db_genre_by_data


@shared_task
def save_genre(genre_info: dict[str, Any], parse_more: bool = False):
    conf = app_settings.GENRE_PARSE_SETTINGS
    current_data = genre_info[conf.CURRENT_KEY]
    current_id = current_data[conf.PARSE_KEYS.id]
    saved_ids = Genre.objects.all().values_list('id', flat=True)
    new_db_genres = []

    if current_id not in saved_ids:
        current_db_genre = get_db_genre_by_data(current_data, fields=conf.PARSE_KEYS)
        new_db_genres.append(current_db_genre)

    saved_children = list(GenreChild.objects.all().values_list('parent_id', 'child_id'))
    new_db_children = []

    for parent in genre_info.get(conf.PARENTS_KEY) or []:
        parent_id = parent[conf.PARSE_KEYS.id]
        if parent_id not in saved_ids:
            new_db_genres.append(get_db_genre_by_data(parent, fields=conf.PARSE_KEYS))

        if (parent_id, current_id) not in saved_children:
            new_db_children.append(GenreChild(parent_id=parent_id, child_id=current_id))

    children = genre_info.get(conf.CHILDREN_KEY, [])
    if parse_more is False:
        for child in children:
            child_id = child[conf.PARSE_KEYS.id]
            if child_id not in saved_ids:
                new_db_genres.append(get_db_genre_by_data(child, fields=conf.PARSE_KEYS))
            if (current_id, child_id) not in saved_children:
                new_db_children.append(GenreChild(parent_id=current_id, child_id=child_id))

    if new_db_genres:
        Genre.objects.bulk_create(new_db_genres)

    if new_db_children:
        GenreChild.objects.bulk_create(new_db_children)

    if parse_more is True:
        for child in children:
            parse_and_save_genres.delay(child['genreId'])


@shared_task
def parse_and_save_genres(genre_id: int = 0, parse_more: bool = False):
    with RakutenRequest() as req:
        genre_info = req.client.genres_search(genre_id)
    save_genre(genre_info, parse_more=parse_more)


@shared_task
def save_product_from_search(search_data):
    genre_info = search_data.get('GenreInformation')

    if genre_info:
        save_genre.delay(genre_info, parse_more=False)

    saved_products = Product.objects.all().values_list('id', 'rakuten_id')
    saved_genre_ids = Genre.objects.all().values_list('id', flat=True)
    saved_products_ids = {r_id: p_id for p_id, r_id in saved_products}
    saved_markers = Marker.objects.all().values_list('name', flat=True)
    new_products, new_details, new_genres, new_markers = [], [], [], []

    for product in search_data.get('Products') or []:
        image_url = product.get('mediumImageUrl') or product.get('smallImageUrl')
        genre_id = product['genreId']

        if genre_id not in saved_genre_ids:
            new_genres.append(
                Genre(
                    id=genre_id,
                    name=product['genreName']
                )
            )
        marker_name = product['makerName']
        if marker_name and marker_name not in saved_markers:
            new_markers.append(Marker(
                rakuten_code=product['makerCode'],
                url=product['makerPageUrlPC'],
                name=product['makerName']
            ))

        product_id = product['productId']

        if product_id not in saved_products_ids.keys():
            db_product = Product(
                rakuten_id=product_id,
                number=product['productNo'],
                name=product['productName'],
                description=product['productCaption'],
                brand_name=product['brandName'],
                genres=[genre_id],
                rank=product['rank'],
                price=product['maxPrice'],
                count=product['itemCount'],
                image_url=image_url.split('?')[0] if image_url else None,
                product_url=product['productUrlPC'],
                release_date=datetime.strptime(product['releaseDate'], "%Y年%m月%d日").date(),
                marker_code=product['makerCode'] if marker_name else '',
                marker=marker_name if marker_name else None
            )
            new_products.append(db_product)
            db_product_id = db_product.id

        else:
            db_product_id = saved_products_ids[product_id]

        for detail in product.get('ProductDetails'):
            match detail:
                case {'name': str() as name, 'value': value}:
                    new_details.append(ProductDetail(product_id=db_product_id, name=name, value=value))

    if new_genres:
        Genre.objects.bulk_create(new_genres)

    if new_markers:
        Marker.objects.bulk_create(new_markers)

    if new_products:
        Product.objects.bulk_create(new_products)

    parse_date()
    if new_details:
        ProductDetail.objects.bulk_create(new_details)


@shared_task
def parse_and_save_products(genre_id: int, keyword: str = None, product_id: int = None, page: int = None):
    with RakutenRequest() as req:
        results = req.client.product_search(
            genre_id=genre_id,
            keyword=keyword,
            product_id=product_id,
            page=page
        )
    save_product_from_search.delay(results)

    for page_num in range(results['pageCount']):
        parse_and_save_products.delay(
            genre_id=genre_id,
            keyword=keyword,
            product_id=product_id,
            page=page_num
        )
