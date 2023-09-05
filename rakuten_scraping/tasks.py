from typing import Any

from django.core.exceptions import ObjectDoesNotExist

from kaimon.celery import app
from product.models import Genre, Product, Tag, ProductImageUrl
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

    if current_id not in db_genre_ids:
        new_genres.append(Genre(**build_genre_fields(current_data, fields=fields)))

    children = genre_data.get(conf.CHILDREN_KEY, [])

    for child in children:
        child_id = child[conf.PARSE_KEYS.id]
        if child_id not in db_genre_ids:
            new_genres.append(Genre(parent_id=current_id, **build_genre_fields(child, fields=fields)))

    if new_genres:
        Genre.objects.bulk_create(new_genres)

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
def save_tags(tags: list[dict]):
    tag_ids = list(map(lambda x: x['tagId'], tags))
    db_tag_ids = list(Tag.objects.filter(id__in=tag_ids).values_list('id', flat=True))
    new_tags = []
    for tag_data in tags:
        tag_id = tag_data['tagId']
        if tag_id in db_tag_ids:
            continue
        new_tags.append(Tag(id=tag_id, name=tag_data['tagName']))
    if new_tags:
        Tag.objects.bulk_create(new_tags)


@app.task()
def save_tags_for_product(product_id: int, new_tags: list[dict[str, Any]], exists_tag_ids: list[int] = None):
    product = Product.objects.get(id=product_id)
    save = False
    if exists_tag_ids:
        product.tags.add(*exists_tag_ids)
        save = True

    new_tags = [
        Tag(
            id=tag['tagGroups'][0]['tags'][0]['tagId'],
            name=tag['tagGroups'][0]['tags'][0]['tagName']
        )
        for tag in new_tags
    ]
    if new_tags:
        tags = Tag.objects.bulk_create(new_tags)
        product.tags.add(*tags)
        save = True

    if save is True:
        product.save()


@app.task()
def parse_tags_for_product(product_id: int, tags_ids: list[int]):
    db_tag_ids = Tag.objects.filter(id__in=tags_ids).values_list('id', flat=True)
    new_tags = []
    exists_tag_ids = []

    for tag_id in tags_ids:
        if tag_id in db_tag_ids:
            exists_tag_ids.append(tag_id)
            continue

        with RakutenRequest(delay=app_settings.DELAY) as rakuten:
            tag_data = rakuten.client.tag_search(tag_id)
            new_tags.append(tag_data)

    if new_tags:
        save_tags_for_product.delay(
            product_id=product_id,
            new_tags=new_tags,
            exists_tag_ids=exists_tag_ids or None
        )


@app.task()
def update_items(items: list[dict[str, Any]]):
    updated_products = []
    update_fields = set()

    for item in items:
        item_code = item['itemCode']
        try:
            db_product = Product.objects.get(id=item_code)
        except ObjectDoesNotExist:
            print('not found product with code %s' % item_code)
            continue

        updated = False
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
    db_product_ids = list(Product.objects.values_list('id', flat=True))
    genres_ids = list(set(get_genre_parents_tree(Genre.objects.get(id=genre_id))))
    to_update_items = []
    new_products, product_images = [], []
    product_tags = {}

    for item in items:
        item_code = item['itemCode']

        if item_code in db_product_ids:
            to_update_items.append(item)
            continue

        tags = item['tagIds']
        product_tags[item_code] = tags
        product = Product(**build_product_fields(item))
        new_products.append(product)

        item_images = item['mediumImageUrls'] or item['smallImageUrls']
        images = [ProductImageUrl(url=url, product_id=item_code) for url in item_images]
        if images:
            product_images.extend(images)

    if new_products:
        products = Product.objects.bulk_create(new_products)
        for product in products:
            product.genres.add(*genres_ids)
            product.save()
            tags = product_tags.get(product.id)
            parse_tags_for_product.delay(product_id=product.id, tags_ids=tags)

    if product_images:
        ProductImageUrl.objects.bulk_create(product_images)

    if to_update_items:
        update_items.delay(to_update_items)


@app.task()
def parse_items(genre_id: int, parse_all: bool = False, page: int = None):
    with RakutenRequest(delay=app_settings.DELAY) as rakuten:
        search_items_data = rakuten.client.item_search(genre_id=genre_id, page=page)

    tag_groups = search_items_data.get('TagInformation')
    for tag_group in tag_groups or []:
        save_tags.delay(tag_group['tags'])

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
