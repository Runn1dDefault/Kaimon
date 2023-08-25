from typing import Any

from django.conf import settings

from kaimon.celery import app
from product.models import Genre, GenreChild, Product, ProductDetail, Marker
from product.tasks import translate_to_fields
from product.utils import get_last_children, get_genre_parents_tree

from .settings import app_settings
from .utils import RakutenRequest, get_db_genre_by_data, collect_product_fields


@app.task()
def save_genre_from_search(genre_info: dict[str, Any], parse_more: bool = False):
    conf = app_settings.GENRE_PARSE_SETTINGS
    current_data = genre_info[conf.CURRENT_KEY]
    if isinstance(current_data, list):
        current_data = current_data[0]
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
        genres = Genre.objects.bulk_create(new_db_genres)

        for genre in genres:
            translate_to_fields.delay(genre.id, settings.GENRE_MODEL_PATH, settings.GENRE_TRANSLATE_FIELDS)

    if new_db_children:
        GenreChild.objects.bulk_create(new_db_children)

    if parse_more is True:
        for child in children:
            parse_and_save_genres.delay(child['genreId'])


@app.task()
def parse_and_save_genres(genre_id: int = 0, parse_more: bool = True):
    with RakutenRequest(delay=app_settings.DELAY) as req:
        genre_info = req.client.genres_search(genre_id)
    save_genre_from_search.delay(genre_info, parse_more=parse_more)


@app.task()
def update_product_after_scrape(product_data: dict[str, Any], product_id: int, genre_id: int, marker_name: str):
    product = Product.objects.get(rakuten_id=product_id)
    save = False

    if genre_id and not product.genres.filter(id=genre_id).exists():
        product.genre = Genre.objects.get(id=genre_id)
        save = True

    if marker_name and product.marker.name != marker_name:
        product.marker = Marker.objects.get(name=marker_name)
        save = True

    product_data = collect_product_fields(product_data)

    for field, value in product_data.items():
        if hasattr(product, field) and getattr(product, field) != value:
            setattr(product, field, value)
            save = True

    details_names = list(product.details.values_list('name', flat=True))
    details = list(product.details.values_list('name', 'value'))

    for detail in product_data.get('ProductDetails') or []:
        match detail:
            case {'name': str() as name, 'value': value} if name not in details_names:
                ProductDetail(product_id=product_id, name=name, value=value).save()
                continue
            case {'name': str() as name, 'value': value} if name in details_names and (name, value) not in details:
                detail = ProductDetail.objects.get(product=product, name=name)
                if detail.value != value:
                    detail.value = value
                    detail.save()
                continue

    if save:
        product.save()


@app.task()
def save_product_from_search(search_data, genre_id: int):
    genre_info = search_data.get('GenreInformation')

    if genre_info:
        save_genre_from_search.delay(genre_info, parse_more=False)

    saved_products = Product.objects.all().values_list('id', 'rakuten_id')
    saved_products_ids = {r_id: p_id for p_id, r_id in saved_products}
    saved_markers = list(Marker.objects.all().values_list('name', flat=True))
    new_products, new_details, new_genres, new_markers = [], [], [], []
    to_update_products = []

    products = search_data.get('Products')
    if not products:
        print("Not found products: ", products)

    for product in products or []:
        marker_name = product['makerName']
        if marker_name and marker_name not in saved_markers:
            new_markers.append(
                Marker(
                    rakuten_code=product['makerCode'],
                    url=product['makerPageUrlPC'],
                    name=product['makerName']
                )
            )
            saved_markers.append(marker_name)

        product_id = product['productId']

        if product_id not in saved_products_ids.keys():
            db_product = Product(
                rakuten_id=product_id,
                marker_id=marker_name or None,
                **collect_product_fields(product)
            )
            new_products.append(db_product)

            for detail in product.get('ProductDetails') or []:
                match detail:
                    case {'name': str() as name, 'value': value} if db_product:
                        new_details.append(
                            ProductDetail(product=db_product, name=name, value=value)
                        )
        else:
            to_update_products.append((product, product_id, genre_id, marker_name))

    if new_markers:
        markers = Marker.objects.bulk_create(new_markers)
        # for marker in markers:
            # translate_to_fields.delay(
            #     instance_id=marker.id,
            #     model_path=settings.MARKER_MODEL_PATH,
            #     fields=settings.MARKER_TRANSLATE_FIELDS
            # )

    if new_products:
        products = Product.objects.bulk_create(new_products)
        genre = Genre.objects.get(id=genre_id)
        genre_parents_ids = get_genre_parents_tree(genre)
        genres = list(Genre.objects.filter(id__in=genre_parents_ids))

        for product in products:
            # translate_to_fields.delay(
            #     instance_id=product.id,
            #     model_path=settings.PRODUCT_MODEL_PATH,
            #     fields=settings.PRODUCT_TRANSLATE_FIELDS
            # )
            product.genres.add(*genres)
            product.save()

    if new_details:
        product_details = ProductDetail.objects.bulk_create(new_details)
        # for product_detail in product_details:
        #     translate_to_fields.delay(
        #         instance_id=product_detail.id,
        #         model_path=settings.PRODUCT_DETAIL_MODEL_PATH,
        #         fields=settings.PRODUCT_DETAIL_TRANSLATE_FIELDS
        #     )

    if to_update_products:
        for args in to_update_products:
            update_product_after_scrape.delay(*args)


@app.task()
def parse_and_save_products(genre_id: int, keyword: str = None, product_id: int = None, page: int = None,
                            parse_all: bool = False):
    with RakutenRequest(delay=app_settings.DELAY) as req:
        results = req.client.product_search(
            genre_id=genre_id,
            keyword=keyword,
            product_id=product_id,
            page=page
        )
    save_product_from_search.delay(results, genre_id)

    if parse_all:
        for page_num in range(2, results['pageCount']):
            parse_and_save_products.delay(
                genre_id=genre_id,
                keyword=keyword,
                product_id=product_id,
                page=page_num
            )


@app.task()
def parse_products():
    base_genres = Genre.objects.filter(level=1)
    for genre in base_genres:
        last_children_ids = get_last_children(genre)
        if not last_children_ids:
            print('Not found child for genre: %s' % genre.id)

        for child_genre in Genre.objects.filter(id__in=last_children_ids):
            parse_and_save_products.delay(child_genre.id, parse_all=True)
