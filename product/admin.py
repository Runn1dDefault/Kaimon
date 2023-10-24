from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from product.filters import ProductRankAdminFilter
from product.models import Genre, GenreTranslation, Tag, TagGroup, Product, ProductTag, ProductGenre, ProductImageUrl, \
    ProductReview, ProductTranslation, TagTranslation, TagGroupTranslation


class GenreTranslationInline(admin.TabularInline):
    model = GenreTranslation
    extra = 0


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    inlines = [GenreTranslationInline]
    list_display = ('id', 'level', 'deactivated')
    search_fields = ('id', 'translations__name',)
    search_help_text = _('Search by fields: ID, NAME')
    list_filter = ('level', 'deactivated')
    fieldsets = (
        (_('General Info'), {'fields': ('id', 'level', 'deactivated')}),
    )
    list_per_page = 30
    list_max_show_all = 50


class ProductImageInline(admin.TabularInline):
    model = ProductImageUrl
    extra = 0


class TagGroupTranslationInline(admin.StackedInline):
    model = TagGroupTranslation
    extra = 0


@admin.register(TagGroup)
class TagGroupAdmin(admin.ModelAdmin):
    inlines = [TagGroupTranslationInline]
    list_display = ('id', 'created_at')
    search_fields = ('id', 'created_at')
    list_filter = ('created_at',)


class TagTranslationInline(admin.StackedInline):
    model = TagTranslation
    extra = 0


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    inlines = [TagTranslationInline]
    list_display = ('id', 'group', 'created_at')
    search_fields = ('id', 'group__translations__name', 'group__id')
    list_filter = ('created_at',)


@admin.register(ProductTag)
class ProductTagAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'tag')
    search_fields = ('product__id', 'tag__id')


@admin.register(ProductGenre)
class ProductGenreAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'genre')
    search_fields = ('product__id', 'genre__id')


class ProductTranslationInline(admin.StackedInline):
    model = ProductTranslation
    extra = 0


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductImageInline, ProductTranslationInline]
    list_display = ('id', 'price', 'is_active', 'availability', 'created_at')
    search_fields = ('id',)
    search_help_text = _('Search by fields: ID, Rakuten ID, NAME, GENRE NAME')
    list_filter = (ProductRankAdminFilter, 'is_active', 'created_at', 'modified_at', 'reference_rank')
    readonly_fields = ('id', 'created_at', 'modified_at')
    fieldsets = (
        (_('General Info'), {'fields': ('id', 'price', 'rakuten_price')}),
        (_('Dates'), {'classes': ['collapse'], 'fields': ('created_at', 'modified_at')}),
        (_('Control'), {'fields': ('availability', 'is_active', 'reference_rank')}),
        (_('Links'), {'classes': ['collapse'], 'fields': ('product_url',)}),
    )
    list_per_page = 30
    list_max_show_all = 50


@admin.register(ProductReview)
class ProductReview(admin.ModelAdmin):
    list_display = ('id', 'product', 'user', 'rank', 'is_active', 'created_at')
    list_display_links = ('id', 'product', 'user')
    search_fields = ('id', 'product_id', 'user__email')
    list_filter = ('is_active', 'created_at')
    readonly_fields = ('created_at', 'modified_at',)
