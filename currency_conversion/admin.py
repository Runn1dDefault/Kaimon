from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Conversion


@admin.register(Conversion)
class ConversionAdmin(admin.ModelAdmin):
    list_display = ('id', 'currency_from', 'currency_to', 'price_per', 'created_at')
    list_display_links = ('id', 'currency_from', 'currency_to',)
    search_fields = ('id',)
    search_help_text = _('Search by ID')
    list_filter = ('currency_from', 'created_at')
