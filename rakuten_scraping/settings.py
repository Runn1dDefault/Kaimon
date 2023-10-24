from copy import deepcopy
from datetime import timedelta
from typing import NamedTuple, Iterable

from django.conf import settings


class GenreParseCase(NamedTuple):
    id: str = 'genreId'
    level: str = 'genreLevel'


class GenreTranslationCase(NamedTuple):
    genre_id: str = 'genreId'
    name: str = 'genreName'


class ProductParseCase(NamedTuple):
    id: str = 'itemCode'
    # here it is not stored in the price field,
    # since price should be calculated with a premium based on the rakuten_price field
    rakuten_price: str = 'itemPrice'
    product_url: str = 'itemUrl'
    availability: str = 'availability'


class ProductTranslationCase(NamedTuple):
    product_id: str = 'itemCode'
    name: str = 'itemName'
    description: str = 'itemCaption'


class TagParseCase(NamedTuple):
    id: str = 'tagId'


class TagTranslationCase(NamedTuple):
    tag_id: str = 'tagId'
    name: str = 'tagName'


class TagGroupParseCase(NamedTuple):
    id: str = 'tagGroupId'


class TagGroupTranslationCase(NamedTuple):
    group_id: str = 'tagGroupId'
    name: str = 'tagGroupName'


class GenreParseSettings(NamedTuple):
    MODEL = 'product.models.Genre'
    TRANS_MODEL = 'product.models.GenreTranslation'
    PARSE_KEYS: GenreParseCase = GenreParseCase()
    TRANS_KEYS: GenreTranslationCase = GenreTranslationCase()
    CURRENT_KEY: str = 'current'
    PARENTS_KEY: str = 'parents'
    CHILDREN_KEY: str = 'children'


class ProductParseSettings(NamedTuple):
    MODEL: str = 'product.models.Product'
    TRANS_MODEL: str = 'product.models.ProductTranslation'
    IMAGE_MODEL: str = 'product.models.ProductImageUrl'
    GENRE_RELATION_MODEL: str = 'product.models.ProductGenre'
    TAG_RELATION_MODEL: str = 'product.models.ProductTag'
    PARSE_KEYS: ProductParseCase = ProductParseCase()
    TRANS_KEYS: ProductTranslationCase = ProductTranslationCase()
    BOOLEAN_FIELDS: Iterable[str] = ('availability',)
    IMG_PARSE_FIELDS: list[str] = ['mediumImageUrls', 'smallImageUrls']
    TAG_IDS_KEY: str = 'tagIds'
    TAG_TMP_NAME: str = 'tmp tag name'
    ITEMS_KEY: str = 'Items'
    TAG_INFO_KEY: str = 'TagInformation'
    PAGES_COUNT_KEY: str = 'pageCount'
    UPDATE_DELTA: timedelta = timedelta(hours=12)


class TagParseSettings(NamedTuple):
    MODEL: str = 'product.models.Tag'
    TRANS_MODEL: str = 'product.models.TagTranslation'
    PARSE_KEYS: TagParseCase = TagParseCase()
    TRANS_KEYS: TagGroupTranslationCase = TagTranslationCase()
    TAG_GROUP_MODEL: str = 'product.models.TagGroup'
    TAG_GROUP_TRANS_MODEL: str = 'product.models.TagGroupTranslation'
    TAG_GROUP_PARSE_KEYS: TagGroupParseCase = TagGroupParseCase()
    TAG_GROUP_TRANS_KEYS: TagGroupTranslationCase = TagGroupTranslationCase()
    TAG_KEY: str = 'tags'
    TAG_GROUP_KEY: str = 'tagGroups'


class AppSettings(NamedTuple):
    CACHE_NAME: str = 'default'
    USED_USER_PREFIX: str = 'busy_client:'
    GENRE_PARSE_SETTINGS: GenreParseSettings = GenreParseSettings()
    PRODUCT_PARSE_SETTINGS: ProductParseSettings = ProductParseSettings()
    TAG_PARSE_SETTINGS: TagParseSettings = TagParseSettings()
    DELAY: float | int = 0.6


def get_app_settings():
    config = deepcopy(settings.PARSING_SETTINGS)

    case_settings = {
        'GENRE_PARSE_SETTINGS': {'PARSE_KEYS': GenreParseCase},
        'PRODUCT_PARSE_SETTINGS': {'PARSE_KEYS': ProductParseCase},
        'TAG_PARSE_SETTINGS': {'PARSE_KEYS': TagParseCase,
                               'TAG_GROUP_PARSE_KEYS': TagGroupParseCase}
    }

    for conf_key, parse_case_classes in case_settings.items():
        parse_conf = config.get(conf_key)
        if parse_conf:

            for conf_field, parse_class in parse_case_classes.items():
                parse_conf[conf_field] = parse_class(**parse_conf.pop(conf_field, dict()))

            config[conf_key] = GenreParseSettings(**parse_conf)
    return AppSettings(**config)


app_settings = get_app_settings()
