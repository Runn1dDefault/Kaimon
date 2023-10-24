from django.db import models
from django.utils.translation import gettext_lazy as _


class LanguageModel(models.Model):
    objects = models.Manager()

    class SupportLanguage(models.TextChoices):
        ja = 'ja', _('Japanese')
        en = 'en', _('English')
        ru = 'ru', _('Russian')
        tr = 'tr', _('Turkish')
        ky = 'ky', _('Kyrgyz')
        kz = 'kk', _('Kazakh')

    # default=SupportLanguage.ja required for scraping!
    language_code = models.CharField(max_length=2, choices=SupportLanguage.choices, default=SupportLanguage.ja)
    name = models.CharField(max_length=100)

    class Meta:
        abstract = True
