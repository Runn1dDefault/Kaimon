from django.core.cache import caches
from django.db import models

from rakuten_scraping.settings import app_settings


class OauthManager(models.Manager):
    _cache = caches[app_settings.CACHE_NAME]

    def active_clients(self):
        return self.get_queryset().filter(disabled=False)

    @staticmethod
    def _get_cache_key(client_id, app_id) -> str:
        return f'{app_settings.USED_USER_PREFIX}:{client_id}_{app_id}'

    def free_client(self):
        while True:
            clients = self.active_clients()

            if clients.exists() is False:
                continue

            for client in clients:
                client_used = self._cache.get(self._get_cache_key(client.id, client.app_id))
                if client_used is None:
                    self.set_busy(client_id=client.id, app_id=client.app_id)
                    return client

    def set_busy(self, client_id, app_id) -> None:
        self._cache.set(self._get_cache_key(client_id, app_id), "1", timeout=None)

    def set_free(self, client_id, app_id) -> None:
        self._cache.delete(self._get_cache_key(client_id, app_id))


class Oauth2Client(models.Model):
    objects = OauthManager()

    app_id = models.BigIntegerField(unique=True)
    secret = models.CharField(max_length=50, blank=True)
    partner_id = models.CharField(max_length=35, blank=True)

    disabled = models.BooleanField(default=False)

    def set_free(self) -> None:
        self.objects.set_free(self.id, self.app_id)
