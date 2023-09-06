from typing import Any

from django.core.exceptions import ObjectDoesNotExist

from kaimon.celery import app
from product.models import Genre, Product, Tag, ProductImageUrl, TagGroup
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
def save_tags_from_groups(tag_groups: list[dict[str, Any]]):
    db_group_ids = list(TagGroup.objects.values_list('id', flat=True))
    db_tag_ids = list(Tag.objects.values_list('id', flat=True))
    new_tags, collected_tag_ids = [], []
    new_groups, collected_group_ids = [], []

    for group in tag_groups:
        group_id = group['tagGroupId']
        if group_id not in db_group_ids and group_id not in collected_group_ids:
            new_groups.append(TagGroup(id=group_id, name=group['tagGroupName']))
            collected_group_ids.append(group_id)

        for tag in group['tags'] or []:
            tag_id = tag['tagId']
            if tag_id in collected_tag_ids:
                continue

            if tag_id not in db_tag_ids:
                new_db_tag = Tag(id=tag_id, name=tag['tagName'], group_id=group_id)
                new_tags.append(new_db_tag)
            collected_tag_ids.append(tag_id)

    if new_groups:
        TagGroup.objects.bulk_create(new_groups)

    if new_tags:
        Tag.objects.bulk_create(new_tags)


@app.task()
def update_or_create_tag(tag_data: dict[str, Any]):
    group = tag_data['tagGroups'][0]
    db_group = TagGroup.objects.get_or_create(id=group['tagGroupId'], name=group['tagGroupName'])
    tag = group['tags'][0]
    db_tag, _ = Tag.objects.get_or_create(id=tag['tagId'])
    if db_tag.group is None or db_tag.group.id != db_group.id:
        db_tag.group = db_group
    db_tag.name = tag['tagName']
    db_tag.save()


@app.task()
def parse_and_update_tag(tag_id: int):
    with RakutenRequest(delay=app_settings.DELAY) as rakuten:
        tag_data = rakuten.client.tag_search(tag_id)
    update_or_create_tag.delay(tag_data)


@app.task()
def save_items(items: list[dict[str, Any]], genre_id: int, tag_groups: list[dict[str, Any]] = None):
    if tag_groups:
        save_tags_from_groups(tag_groups)

    db_product_ids = list(Product.objects.values_list('id', flat=True))
    db_tag_ids = list(Tag.objects.values_list('id', flat=True))
    db_genres_ids = list(set(get_genre_parents_tree(Genre.objects.get(id=genre_id))))

    to_update_items = []
    new_products, product_images = [], []
    new_tags, new_tag_ids = [], []

    product_tags = {}

    for item in items:
        item_code = item['itemCode']

        if item_code in db_product_ids:
            to_update_items.append(item)
            continue

        tag_ids = item['tagIds']
        if tag_ids:
            for tag_id in tag_ids:
                if tag_id not in db_tag_ids and tag_id not in new_tag_ids:
                    new_tags.append(Tag(id=tag_id, name='in_scraping'))
                    new_tag_ids.append(tag_id)

            product_tags[item_code] = tag_ids

        product = Product(**build_product_fields(item))
        new_products.append(product)

        item_images = item['mediumImageUrls'] or item['smallImageUrls']
        image_urls = list(map(lambda url: ProductImageUrl(product_id=item_code, url=url.split('?')[0]), item_images))
        if image_urls:
            product_images.extend(image_urls)

    if new_tags:
        Tag.objects.bulk_create(new_tags)

        for tag in new_tags:
            parse_and_update_tag.delay(tag.id)

    if new_products:
        products = Product.objects.bulk_create(new_products)

        for product in products:
            product.genres.add(*db_genres_ids)
            if product.id in product_tags:
                product.tags.add(*product_tags[product.id])
            product.save()

    if product_images:
        ProductImageUrl.objects.bulk_create(product_images)

    if to_update_items:
        update_items.delay(to_update_items)


@app.task()
def parse_items(genre_id: int, parse_all: bool = False, page: int = None):
    with RakutenRequest(delay=app_settings.DELAY) as rakuten:
        search_items_data = rakuten.client.item_search(genre_id=genre_id, page=page)

    save_items.delay(search_items_data['Items'], genre_id, tag_groups=search_items_data.get('TagInformation'))

    for page_num in range(2, search_items_data['pageCount']) if parse_all else []:
        parse_items.delay(genre_id=genre_id, page=page_num)


@app.task()
def parse_all_genre_products():
    base_genres = Genre.objects.filter(level=1)
    for genre in base_genres:
        children = get_last_children(genre)

        for child_id in children:
            parse_items.delay(child_id, parse_all=True)
