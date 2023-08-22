from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from product.models import Genre, GenreChild, Product, Marker, ProductDetail


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'level')
    list_display_links = ('id', 'name')
    search_fields = ('id', 'name', 'name_tr', 'name_ru', 'name_en', 'name_ky', 'name_de')
    search_help_text = _('Search by fields: ID, NAME')
    list_filter = ('level',)
    fieldsets = (
        (_('General Info'), {'fields': ('id', 'name', 'level')}),
        (_('Another language names'), {'fields': ('name_tr', 'name_ru', 'name_en', 'name_ky', 'name_de')}),
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
    search_fields = ('id', 'rakuten_id', 'name', 'name_tr', 'name_ru', 'name_en', 'name_ky', 'name_de')
    search_help_text = _('Search by fields: ID, Rakuten ID, NAME')
    list_filter = ('is_active', 'release_date',)
    readonly_fields = ('created_at', 'modified_at')
    fieldsets = (
        (
            _('General Info'),
            {'fields': ('rakuten_id', 'name', 'brand_name', 'description', 'price', 'genres', 'rank', 'count')}
        ),
        (_('Important dates'), {'fields': ('release_date', 'created_at', 'modified_at')}),
        (_('Marker'), {'fields': ('marker', 'marker_code')}),
        (_('Control'), {'fields': ('is_active',)}),
        (_('Links'), {'fields': ('image_url', 'product_url')}),
        (
            _('Another language fields'),
            {'fields': ('name_tr', 'name_ru', 'name_en', 'name_ky', 'name_de', 'description_tr', 'description_ru',
                        'description_en', 'description_ky', 'description_de')}
        )
    )


@admin.register(Marker)
class MarkerAdmin(admin.ModelAdmin):
    list_display = ('name',)
    list_display_links = ('name',)
    search_fields = ('name', 'name_tr', 'name_ru', 'name_en', 'name_ky', 'name_de',)
    search_help_text = _('Search by Marker name')


@admin.register(ProductDetail)
class ProductDetailAdmin(admin.ModelAdmin):
    list_display = ('name', 'value', 'product')
    list_display_links = ('name', 'value')
    search_fields = ('product__id', 'name', 'name_tr', 'name_ru', 'name_en', 'name_ky', 'name_de', 'value', 'value_tr',
                     'value_ru', 'value_en', 'value_ky', 'value_de')
    search_help_text = _('Search By fields: Product ID, Name, Value')
    fieldsets = (
        (None, {'fields': ('product', 'name', 'value')}),
        (
            _('Another language fields'),
            {'fields': ('name_tr', 'name_ru', 'name_en', 'name_ky', 'name_de', 'value_tr', 'value_ru', 'value_en',
                        'value_ky', 'value_de')})
    )
