from typing import Any

from django.core.exceptions import ObjectDoesNotExist

from kaimon.celery import app
from product.models import Genre, Product, Tag
from product.utils import get_genre_parents_tree, get_last_children

from .settings import app_settings
from .utils import RakutenRequest, build_genre_fields, build_product_fields


@app.task()
def save_genre(genre_data: dict[str, Any], parse_more: bool = False):
    conf = app_settings.GENRE_PARSE_SETTINGS

    current_data = genre_data[conf.CURRENT_KEY]
    if isinstance(current_data, list):
        current_data = current_data[0]

    current_id = current_data[conf.PARSE_KEYS.id]
    db_genres = {genre.id: genre for genre in Genre.objects.all()}
    db_genre_ids = list(db_genres.keys())
    fields = conf.PARSE_KEYS._asdict()

    new_genres = []
    to_update_parent = []

    if current_id not in db_genre_ids:
        new_genres.append(Genre(**build_genre_fields(current_data, fields=fields)))

    children = genre_data.get(conf.CHILDREN_KEY, [])

    for child in children:
        child_id = child[conf.PARSE_KEYS.id]
        if child_id not in db_genre_ids:
            new_genres.append(Genre(parent_id=current_id, **build_genre_fields(child, fields=fields)))
        else:
            db_genre = db_genres[child_id]
            if db_genre.parent_id == current_id:
                continue
            db_genre.parent_id = current_id
            to_update_parent.append(db_genre)

    if new_genres:
        Genre.objects.bulk_create(new_genres)

    if to_update_parent:
        Genre.objects.bulk_update(to_update_parent, ['parent_id'])

    if parse_more:
        for child in children:
            child_id = child[conf.PARSE_KEYS.id]
            parse_genres.delay(child_id, parse_more=parse_more)


@app.task()
def parse_genres(genre_id: int = 0, parse_more: bool = False):
    with RakutenRequest(delay=app_settings.DELAY) as rakuten:
        genre_info = rakuten.client.genres_search(genre_id)
    save_genre.delay(genre_info, parse_more=parse_more)


@app.task()
def parse_tags(tags_ids: list[int]):
    new_tags = []

    for tag_id in tags_ids:
        with RakutenRequest(delay=app_settings.DELAY) as rakuten:
            tag_info = rakuten.client.tag_search(tag_id)

        group = tag_info['tagGroups'][0]
        tag = group['tags'][0]
        new_tags.append(Tag(id=tag['tagId'], parent_id=tag['parentTagId']))

    if new_tags:
        Tag.objects.bulk_create(new_tags)


@app.task()
def update_items(items: list[dict[str, Any]]):
    db_tag_ids = list(Tag.objects.values_list('id', flat=True))
    updated_products = []
    update_fields = set()

    for item in items:
        item_code = item['itemCode']
        try:
            db_product = Product.objects.get(code=item_code)
        except ObjectDoesNotExist:
            print('not found product with code %s' % item_code)
            continue

        updated = False
        tags = item.pop('tagIds', [])
        if tags:
            product_tag_ids = list(db_product.tags.values_list('id', flat=True))

            if tags != product_tag_ids:
                for tag_id in tags:
                    if tag_id not in db_tag_ids:
                        parse_tags(tags_ids=[tag_id])

                    if tag_id not in product_tag_ids:
                        db_product.tags.add(tag_id)
                        update_fields.add('tags')
                        updated = True

        collected_db_fields = build_product_fields(item)
        for field, value in collected_db_fields.items():
            if hasattr(db_product, field) and getattr(db_product, field) != value:
                setattr(db_product, field, value)
                update_fields.add(field)
                updated = True
        if updated:
            updated_products.append(db_product)

    if updated_products:
        Product.objects.bulk_update(updated_products, update_fields)


@app.task()
def save_items(items: list[dict[str, Any]], genre_id: int):
    db_products_codes = list(Product.objects.values_list('item_code', flat=True))
    db_tag_ids = list(Tag.objects.values_list('id', flat=True))
    genres_ids = list(set(get_genre_parents_tree(Genre.objects.get(id=genre_id))))

    to_update_items = []
    new_products = []
    product_tags = {}

    for item in items:
        item_code = item['itemCode']

        if item_code in db_products_codes:
            to_update_items.append(item)
            continue

        tags = item['tagIds']
        if tags not in db_tag_ids:
            parse_tags(tags)

        product_tags[item_code] = tags
        product = Product(genre_id=genre_id, **build_product_fields(item))
        product.tags.add(**tags)
        product.related_genres.add(*genres_ids)
        new_products.append(product)

    if new_products:
        Product.objects.bulk_create(new_products)

    if to_update_items:
        update_items.delay(to_update_items)


@app.task()
def parse_items(genre_id: int, parse_all: bool = False, page: int = None):
    with RakutenRequest(delay=app_settings.DELAY) as rakuten:
        search_items_data = rakuten.client.item_search(genre_id=genre_id, page=page)

    save_items.delay(search_items_data['Items'], genre_id)

    for page_num in range(2, search_items_data['pageCount']) if parse_all else []:
        parse_items.delay(genre_id=genre_id, page=page_num)


@app.task()
def parse_all_genre_products():
    base_genres = Genre.objects.filter(level=1)
    for genre in base_genres:
        children = get_last_children(genre)

        for child_id in children:
            parse_items.delay(child_id, parse_all=True)
