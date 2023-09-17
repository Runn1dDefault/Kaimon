import logging
from typing import Any

from django.core.exceptions import ObjectDoesNotExist

from kaimon.celery import app
from product.utils import get_genre_parents_tree, get_last_children
from utils.helpers import import_model

from .settings import app_settings
from .utils import get_rakuten_client, build_by_fields_map


# --------------------------------------- DB SAVING AND UPDATING TASK's ------------------------------------------------
@app.task()
def save_genre(genre_data: dict[str, Any], parse_more: bool = False):
    conf = app_settings.GENRE_PARSE_SETTINGS
    fields_map = conf.PARSE_KEYS._asdict()
    genre_model = import_model(conf.MODEL)

    current_data = genre_data[conf.CURRENT_KEY]
    if isinstance(current_data, list):
        current_data = current_data[0]

    current_id = current_data[conf.PARSE_KEYS.id]
    saved_genre_ids = list(genre_model.objects.values_list('id', flat=True))
    new_genres = []

    if current_id not in saved_genre_ids:
        new_genres.append(genre_model(**build_by_fields_map(current_data, fields_map=fields_map)))

    children = genre_data.get(conf.CHILDREN_KEY) or []
    for child in children:
        if child[conf.PARSE_KEYS.id] not in saved_genre_ids:
            new_child_genre = genre_model(parent_id=current_id, **build_by_fields_map(child, fields_map=fields_map))
            new_genres.append(new_child_genre)

    if new_genres:
        genre_model.objects.bulk_create(new_genres)

    for child in children if parse_more else []:
        child_id = child[conf.PARSE_KEYS.id]
        parse_genres.delay(child_id, parse_more=parse_more)


@app.task()
def save_tags(tags: list[dict]):
    conf = app_settings.TAG_PARSE_SETTINGS
    tag_model = import_model(conf.MODEL)
    tag_ids = list(map(lambda x: x[conf.PARSE_KEYS.id], tags))
    db_tag_ids = list(tag_model.objects.filter(id__in=tag_ids).values_list('id', flat=True))
    new_tags = []
    for tag_data in tags:
        tag_id = tag_data[conf.PARSE_KEYS.id]
        if tag_id in db_tag_ids:
            continue
        new_tags.append(tag_model(id=tag_id, name=tag_data[conf.PARSE_KEYS.name]))
    if new_tags:
        tag_model.objects.bulk_create(new_tags)


@app.task()
def save_tags_from_groups(tag_groups: list[dict[str, Any]]):
    conf = app_settings.TAG_PARSE_SETTINGS
    tag_group_model = import_model(conf.TAG_GROUP_MODEL)
    tag_model = import_model(conf.MODEL)
    db_group_ids = list(tag_group_model.objects.values_list('id', flat=True))
    db_tag_ids = list(tag_model.objects.values_list('id', flat=True))
    new_tags, collected_tag_ids = [], []
    new_groups, collected_group_ids = [], []

    for group in tag_groups:
        group_id = group[conf.TAG_GROUP_PARSE_KEYS.id]
        if group_id not in db_group_ids and group_id not in collected_group_ids:
            new_groups.append(tag_group_model(id=group_id, name=group[conf.TAG_GROUP_PARSE_KEYS.name]))
            collected_group_ids.append(group_id)

        for tag in group[conf.TAG_KEY] or []:
            tag_id = tag[conf.PARSE_KEYS.id]
            if tag_id in collected_tag_ids:
                continue

            if tag_id not in db_tag_ids:
                new_db_tag = tag_model(id=tag_id, name=tag[conf.PARSE_KEYS.name], group_id=group_id)
                new_tags.append(new_db_tag)
            collected_tag_ids.append(tag_id)

    if new_groups:
        tag_group_model.objects.bulk_create(new_groups)

    if new_tags:
        tag_model.objects.bulk_create(new_tags)


@app.task()
def update_or_create_tag(tag_data: dict[str, Any]):
    conf = app_settings.TAG_PARSE_SETTINGS
    tag_group_model = import_model(conf.TAG_GROUP_MODEL)
    tag_model = import_model(conf.MODEL)

    group = tag_data[conf.TAG_GROUP_KEY][0]
    db_group = tag_group_model.objects.get_or_create(
        id=group[conf.TAG_GROUP_PARSE_KEYS.id],
        name=group[conf.TAG_GROUP_PARSE_KEYS.name]
    )
    tag = group[conf.TAG_KEY][0]
    db_tag, _ = tag_model.objects.get_or_create(id=tag[conf.PARSE_KEYS.id])
    if db_tag.group is None or db_tag.group.id != db_group.id:
        db_tag.group = db_group
    db_tag.name = tag[conf.PARSE_KEYS.name]
    db_tag.save()


@app.task()
def update_items(items: list[dict[str, Any]]):
    conf = app_settings.PRODUCT_PARSE_SETTINGS
    product_model = import_model(conf.MODEL)
    fields_map = conf.PARSE_KEYS._asdict()
    updated_products, update_fields = [], set()

    for item in items:
        item_code = item[conf.PARSE_KEYS.id]
        try:
            db_product = product_model.objects.get(id=item_code)
        except ObjectDoesNotExist:
            logging.warning('not found product with code %s' % item_code)
            continue

        updated = False
        collected_db_fields = build_by_fields_map(item, fields_map=fields_map)
        for field, value in collected_db_fields.items():
            if hasattr(db_product, field) and getattr(db_product, field) != value:
                setattr(db_product, field, value)
                update_fields.add(field)
                updated = True
        if updated:
            updated_products.append(db_product)

    if updated_products:
        product_model.objects.bulk_update(updated_products, update_fields)


@app.task()
def save_items(items: list[dict[str, Any]], genre_id: int, tag_groups: list[dict[str, Any]] = None):
    conf = app_settings.PRODUCT_PARSE_SETTINGS
    tag_conf = app_settings.TAG_PARSE_SETTINGS
    product_model = import_model(conf.MODEL)
    img_model = import_model(conf.IMAGE_MODEL)
    tag_model = import_model(tag_conf.MODEL)
    genre_model = import_model(app_settings.GENRE_PARSE_SETTINGS.MODEL)
    fields_map = conf.PARSE_KEYS._asdict()

    if tag_groups:
        save_tags_from_groups(tag_groups)

    db_product_ids = list(product_model.objects.values_list('id', flat=True))
    db_tag_ids = list(tag_model.objects.values_list('id', flat=True))
    db_genres_ids = list(set(get_genre_parents_tree(genre_model.objects.get(id=genre_id))))

    to_update_items = []
    new_products, product_images = [], []
    new_tags, new_tag_ids = [], []

    product_tags = {}

    for item in items:
        item_code = item[conf.PARSE_KEYS.id]

        if item_code in db_product_ids:
            to_update_items.append(item)
            continue

        tag_ids = item[conf.TAG_IDS_KEY]
        if tag_ids:
            for tag_id in tag_ids:
                if tag_id not in db_tag_ids and tag_id not in new_tag_ids:
                    new_tags.append(tag_model(id=tag_id, name=conf.TAG_TMP_NAME))
                    new_tag_ids.append(tag_id)

            product_tags[item_code] = tag_ids

        new_products.append(product_model(**build_by_fields_map(item, fields_map=fields_map)))

        for img_key in conf.IMG_PARSE_FIELDS or []:
            image_urls = item.get(img_key)

            if not image_urls:
                continue

            image_instances = list(
                map(
                    lambda url: img_model(
                        product_id=item_code,
                        url=url.split('?')[0]
                    ), image_urls)
            )
            if image_instances:
                product_images.extend(image_instances)
                break

    if new_tags:
        tag_model.objects.bulk_create(new_tags)

        for tag in new_tags:
            parse_and_update_tag.delay(tag.id)

    if new_products:
        products = product_model.objects.bulk_create(new_products)

        for product in products:
            product.genres.add(*db_genres_ids)
            if product.id in product_tags:
                product.tags.add(*product_tags[product.id])
            product.save()

    if product_images:
        img_model.objects.bulk_create(product_images)

    if to_update_items:
        update_items.delay(to_update_items)


# ----------------------------------------------- REQUEST's TASK's -----------------------------------------------------

@app.task()
def parse_genres(genre_id: int = 0, parse_more: bool = False):
    rakuten = get_rakuten_client(app_settings.DELAY)
    genre_info = rakuten.genres_search(genre_id)
    save_genre.delay(genre_info, parse_more=parse_more)


@app.task()
def parse_items(genre_id: int, parse_all: bool = False, page: int = None):
    conf = app_settings.PRODUCT_PARSE_SETTINGS
    rakuten = get_rakuten_client(app_settings.DELAY)
    items_data = rakuten.item_search(genre_id=genre_id, page=page)
    save_items.delay(
        items_data[conf.ITEMS_KEY],
        genre_id,
        tag_groups=items_data.get(conf.TAG_INFO_KEY) or None
    )

    for page_num in range(2, items_data[conf.PAGES_COUNT_KEY]) if parse_all else []:
        parse_items.delay(genre_id=genre_id, page=page_num)


@app.task()
def parse_and_update_tag(tag_id: int):
    rakuten = get_rakuten_client(delay=app_settings.DELAY)
    tag_data = rakuten.tag_search(tag_id)
    update_or_create_tag.delay(tag_data)


@app.task()
def check_products_availability(product_id: str):
    conf = app_settings.PRODUCT_PARSE_SETTINGS
    product_model = import_model(conf.PRODUCT_MODEL)
    product = product_model.objects.get(id=product_id)
    rakuten = get_rakuten_client(app_settings.DELAY, validation_client=True)
    items_data = rakuten.item_search(item_code=product_id).get(conf.ITEMS_KEY) or []
    if not items_data:
        product.availability = False
        # don't add product.is_active=False here, it adds overhead when updating the product
        product.save()


# ---------------------------------------------- TOTAL TASK's ----------------------------------------------------------
@app.task()
def parse_all_genre_products():
    genre_model = import_model(app_settings.GENRE_PARSE_SETTINGS.MODEL)
    for genre in genre_model.objects.filter(level=1):
        children = get_last_children(genre)

        for child_id in children:
            parse_items.delay(child_id, parse_all=True)


