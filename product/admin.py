from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from product.filters import ProductRankAdminFilter
from product.models import Genre, Product, ProductImageUrl, ProductReview, Tag


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'level', 'deactivated')
    list_display_links = ('id', 'name')
    search_fields = ('id', 'name', 'name_tr', 'name_ru', 'name_en', 'name_ky', 'name_kz')
    search_help_text = _('Search by fields: ID, NAME')
    list_filter = ('level', 'deactivated')
    fieldsets = (
        (_('General Info'), {'fields': ('id', 'name', 'level', 'deactivated')}),
        (_('Another language names'), {'fields': ('name_tr', 'name_ru', 'name_en', 'name_ky', 'name_kz')}),
    )
    list_per_page = 30
    list_max_show_all = 50


class ProductImageInline(admin.TabularInline):
    model = ProductImageUrl
    extra = 0


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('id', 'name',)
    list_filter = ('created_at',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductImageInline]
    list_display = ('id', 'name', 'price', 'is_active', 'availability', 'created_at')
    list_display_links = ('id', 'name')
    search_fields = ('id', 'code', 'name', 'name_tr', 'name_ru', 'name_en', 'name_ky', 'name_kz',
                     'tag__name', 'tag__name_ru', 'tag__name_en', 'tag__name_ky', 'tag__name_kz', 'tag__name_tr')
    search_help_text = _('Search by fields: ID, Rakuten ID, NAME, GENRE NAME')
    list_filter = (ProductRankAdminFilter, 'is_active', 'created_at', 'modified_at')
    readonly_fields = ('created_at', 'modified_at')
    fieldsets = (
        (
            _('General Info'),
            {'fields': ('code', 'name', 'description', 'price',)}
        ),
        (_('Dates'), {'classes': ['collapse'], 'fields': ('created_at', 'modified_at')}),
        (_('Control'), {'fields': ('is_active',)}),
        (_('Links'), {'classes': ['collapse'], 'fields': ('product_url',)}),
        (
            _('Another language fields'),
            {
                'classes': ['collapse'],
                'fields': ('name_tr', 'name_ru', 'name_en', 'name_ky', 'name_kz', 'description_tr', 'description_ru',
                           'description_en', 'description_ky', 'description_kz',)
            }
        )
    )
    list_per_page = 30
    list_max_show_all = 50


@admin.register(ProductReview)
class ProductReview(admin.ModelAdmin):
    list_display = ('id', 'product', 'user', 'rank', 'is_active', 'created_at')
    list_display_links = ('id', 'product', 'user')
    search_fields = ('id', 'product_id', 'user__email')
    list_filter = ('is_active', 'created_at')
    readonly_fields = ('created_at', 'modified_at')
