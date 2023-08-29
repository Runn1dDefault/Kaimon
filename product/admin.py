from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from product.filters import ProductRankAdminFilter, ProductHasDetailAdminFilter
from product.models import Genre, GenreChild, Product, Marker, ProductDetail, ProductReview


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'level')
    list_display_links = ('id', 'name')
    search_fields = ('id', 'name', 'name_tr', 'name_ru', 'name_en', 'name_ky', 'name_kz')
    search_help_text = _('Search by fields: ID, NAME')
    list_filter = ('level',)
    fieldsets = (
        (_('General Info'), {'fields': ('id', 'name', 'level')}),
        (_('Another language names'), {'fields': ('name_tr', 'name_ru', 'name_en', 'name_ky', 'name_kz')}),
    )
    list_per_page = 30
    list_max_show_all = 50


@admin.register(GenreChild)
class GenreChildAdmin(admin.ModelAdmin):
    list_display = ('id', 'parent', 'child')
    list_display_links = ('id', 'parent', 'child')
    search_fields = ('parent__id', 'child__id', 'parent__name', 'child__name')
    list_filter = ('child__level',)
    list_per_page = 30
    list_max_show_all = 50


class ProductDetailInline(admin.StackedInline):
    verbose_name = _('Details')
    model = ProductDetail
    extra = 0
    fieldsets = (
        (
            _('D...'),
            {'classes': ['collapse'], 'fields': ('name', 'value', 'name_ru', 'value_ru', 'name_en', 'value_en',
                                                 'name_tr', 'value_tr', 'name_ky', 'value_ky', 'name_kz', 'value_kz')}
        ),
    )


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductDetailInline]
    list_display = ('id', 'rakuten_id', 'name', 'price', 'is_active', 'release_date')
    list_display_links = ('id', 'rakuten_id', 'name')
    search_fields = ('id', 'rakuten_id', 'name', 'name_tr', 'name_ru', 'name_en', 'name_ky', 'name_kz', 'genres__name',
                     'brand_name', 'brand_name_tr', 'brand_name_ru', 'brand_name_en', 'brand_name_ky', 'brand_name_kz')
    search_help_text = _('Search by fields: ID, Rakuten ID, NAME, GENRE NAME')
    list_filter = (ProductHasDetailAdminFilter, ProductRankAdminFilter, 'is_active', 'release_date',)
    readonly_fields = ('created_at', 'modified_at')
    fieldsets = (
        (
            _('General Info'),
            {'fields': ('rakuten_id', 'name', 'brand_name', 'description', 'price', 'genres', 'rank', 'count')}
        ),
        (_('Dates'), {'classes': ['collapse'], 'fields': ('release_date', 'created_at', 'modified_at')}),
        (_('Marker'), {'classes': ['collapse'], 'fields': ('marker', 'marker_code')}),
        (_('Control'), {'fields': ('is_active',)}),
        (_('Links'), {'classes': ['collapse'], 'fields': ('image_url', 'product_url')}),
        (
            _('Another language fields'),
            {
                'classes': ['collapse'],
                'fields': ('name_tr', 'name_ru', 'name_en', 'name_ky', 'name_kz', 'description_tr', 'description_ru',
                           'description_en', 'description_ky', 'description_kz', 'brand_name_tr',
                           'brand_name_ru', 'brand_name_en', 'brand_name_ky', 'brand_name_kz')
            }
        )
    )
    filter_horizontal = ("genres",)
    list_per_page = 30
    list_max_show_all = 50


@admin.register(Marker)
class MarkerAdmin(admin.ModelAdmin):
    list_display = ('name',)
    list_display_links = ('name',)
    search_fields = ('name', 'name_tr', 'name_ru', 'name_en', 'name_ky', 'name_kz',)
    search_help_text = _('Search by Marker name')


@admin.register(ProductReview)
class ProductReview(admin.ModelAdmin):
    list_display = ('id', 'product', 'user', 'rank', 'is_active', 'created_at')
    list_display_links = ('id', 'product', 'user')
    search_fields = ('id', 'product_id', 'user__email')
    list_filter = ('is_active', 'created_at')
    readonly_fields = ('created_at', 'modified_at')
