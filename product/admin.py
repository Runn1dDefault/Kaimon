from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from product.filters import ProductRankAdminFilter
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


@admin.register(GenreChild)
class GenreChildAdmin(admin.ModelAdmin):
    list_display = ('id', 'parent', 'child')
    list_display_links = ('id', 'parent', 'child')
    search_fields = ('parent__id', 'child__id', 'parent__name', 'child__name')
    list_filter = ('child__level',)


class ProductDetailInline(admin.TabularInline):
    verbose_name = _('Details')
    model = ProductDetail
    fields = ('name', 'value')
    extra = 0


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductDetailInline]
    list_display = ('id', 'rakuten_id', 'name', 'price', 'is_active', 'release_date')
    list_display_links = ('id', 'rakuten_id', 'name')
    search_fields = ('id', 'rakuten_id', 'name', 'name_tr', 'name_ru', 'name_en', 'name_ky', 'name_kz', 'genres__name',
                     'brand_name', 'brand_name_tr', 'brand_name_ru', 'brand_name_en', 'brand_name_ky', 'brand_name_kz')
    search_help_text = _('Search by fields: ID, Rakuten ID, NAME, GENRE NAME')
    list_filter = (ProductRankAdminFilter, 'is_active', 'release_date',)
    readonly_fields = ('created_at', 'modified_at')
    fieldsets = (
        (
            _('General Info'),
            {'fields': ('rakuten_id', 'name', 'brand_name', 'description', 'price', 'genres', 'rank', 'count')}
        ),
        (_('Dates'), {'fields': ('release_date', 'created_at', 'modified_at')}),
        (_('Marker'), {'fields': ('marker', 'marker_code')}),
        (_('Control'), {'fields': ('is_active',)}),
        (_('Links'), {'fields': ('image_url', 'product_url')}),
        (
            _('Another language fields'),
            {'fields': ('name_tr', 'name_ru', 'name_en', 'name_ky', 'name_kz', 'description_tr', 'description_ru',
                        'description_en', 'description_ky', 'description_kz', 'brand_name_tr',
                        'brand_name_ru', 'brand_name_en', 'brand_name_ky', 'brand_name_kz')}
        )
    )
    filter_horizontal = ("genres",)


@admin.register(Marker)
class MarkerAdmin(admin.ModelAdmin):
    list_display = ('name',)
    list_display_links = ('name',)
    search_fields = ('name', 'name_tr', 'name_ru', 'name_en', 'name_ky', 'name_kz',)
    search_help_text = _('Search by Marker name')


@admin.register(ProductDetail)
class ProductDetailAdmin(admin.ModelAdmin):
    list_display = ('name', 'value', 'product')
    list_display_links = ('name', 'value')
    search_fields = ('product__id', 'name', 'name_tr', 'name_ru', 'name_en', 'name_ky', 'name_kz', 'value', 'value_tr',
                     'value_ru', 'value_en', 'value_ky', 'value_kz')
    search_help_text = _('Search By fields: Product ID, Name, Value')
    fieldsets = (
        (None, {'fields': ('product', 'name', 'value')}),
        (
            _('Another language fields'),
            {'fields': ('name_tr', 'name_ru', 'name_en', 'name_ky', 'name_kz', 'value_tr', 'value_ru', 'value_en',
                        'value_ky', 'value_kz')})
    )


@admin.register(ProductReview)
class ProductReview(admin.ModelAdmin):
    list_display = ('id', 'product', 'user', 'rank', 'is_active', 'created_at')
    list_display_links = ('id', 'product', 'user')
    search_fields = ('id', 'product_id', 'user__email')
    list_filter = ('is_active', 'created_at')
    readonly_fields = ('created_at', 'modified_at')
