import logging
import time

from django.core.cache import caches
from django.db import models

from rakuten_scraping.settings import app_settings


def oauth_user_cache_key(client_id, app_id) -> str:
    return f'{app_settings.USED_USER_PREFIX}:{client_id}_{app_id}'


class CacheOauthManager(models.Manager):
    _cache = caches[app_settings.CACHE_NAME]

    def set_busy(self, client_id, app_id, delay: int | float = None) -> None:
        self._cache.set(oauth_user_cache_key(client_id, app_id), "1", timeout=delay)

    def set_free(self, client_id, app_id) -> None:
        self._cache.delete(oauth_user_cache_key(client_id, app_id))

    def active_clients(self):
        return self.filter(disabled=False)

    def free_client(self, to_validation: bool = False):
        # future: perhaps you should allocate free clients based on a minimum amount of usage
        #  and usage amount stored in cache
        logging.info('Search free client...')
        st = time.monotonic()
        while True:
            clients = self.active_clients().filter(to_validation=to_validation)

            if clients.exists() is False:
                continue

            for client in clients:
                client_used = self._cache.get(oauth_user_cache_key(client.id, client.app_id))
                if client_used is None:
                    logging.info(f'Found free client {time.monotonic() - st}')
                    return client


class Oauth2Client(models.Model):
    objects = models.Manager()
    cached_objects = CacheOauthManager()

    app_id = models.BigIntegerField(unique=True)
    secret = models.CharField(max_length=50, blank=True, null=True)
    partner_id = models.CharField(max_length=35, blank=True, null=True)

    disabled = models.BooleanField(default=False)
    to_validation = models.BooleanField(default=False)

