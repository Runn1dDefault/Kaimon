from copy import deepcopy
from typing import NamedTuple

from django.conf import settings


class GenrePaseKeys(NamedTuple):
    id: str = 'genreId'
    level: str = 'genreLevel'
    name: str = 'genreName'


class GenreParseSettings(NamedTuple):
    PARSE_KEYS: GenrePaseKeys = GenrePaseKeys()
    CURRENT_KEY: str = 'current'
    PARENTS_KEY: str = 'parents'
    CHILDREN_KEY: str = 'children'


class AppSettings(NamedTuple):
    CACHE_NAME: str = 'default'
    USED_USER_PREFIX: str = 'busy_client:'
    GENRE_PARSE_SETTINGS: GenreParseSettings = GenreParseSettings()


def get_app_settings():
    config = deepcopy(settings.RAKUTEN_PARSING_SETTINGS)

    genre_pase_conf = config.get('GENRE_PARSING')
    if genre_pase_conf:
        parse_keys = GenrePaseKeys(**genre_pase_conf.pop('PARSE_KEYS', dict()))
        config['GENRE_PARSING'] = GenreParseSettings(
            PARSE_KEYS=parse_keys,
            **genre_pase_conf
        )

    return AppSettings(**config)


app_settings = get_app_settings()
