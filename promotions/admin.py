from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Banner, Promotion, Discount


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'created_at')
    list_display_links = ('id', 'name',)
    list_filter = ('created_at', )
    search_fields = ('id', 'name',)
    search_help_text = _('Search by field: ID, Name')


class DiscountAdminInline(admin.StackedInline):
    model = Discount


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    inlines = [DiscountAdminInline]
    list_display = ('id', 'start_date', 'end_date', 'created_at')
    list_filter = ('start_date', 'end_date', 'created_at')
    search_fields = ('id',)
    search_help_text = _('Search By ID')