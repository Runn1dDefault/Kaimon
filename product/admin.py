# from django.contrib import admin
# from django.utils.translation import gettext_lazy as _
#
# from product.models import Genre, Tag, TagGroup, Product, ProductImageUrl, ProductReview
#
#
# admin.site.site_header = "Dev Admin"
# admin.site.index_title = "Welcome to Dev Admin"
# admin.site.site_title = "Dev Admin"
#
#
# @admin.action(description="Mark selected genres as activated")
# def make_active(modeladmin, request, queryset):
#     queryset.update(deactivated=False)
#
#
# @admin.action(description="Mark selected genres as deactivated")
# def make_deactivated(modeladmin, request, queryset):
#     queryset.update(deactivated=True)
#
#
# @admin.register(Genre)
# class GenreAdmin(admin.ModelAdmin):
#     list_display = ('id', 'name', 'level', 'deactivated')
#     list_display_links = ('id', 'name')
#     search_fields = ('id', 'name')
#     search_help_text = _('Search by fields: ID, NAME')
#     list_filter = ('level', 'deactivated')
#     list_per_page = 30
#     list_max_show_all = 50
#     actions = [make_active]
#
#
# class ProductImageInline(admin.TabularInline):
#     model = ProductImageUrl
#     extra = 0
#
#
# @admin.register(TagGroup)
# class TagGroupAdmin(admin.ModelAdmin):
#     list_display = ('id', 'name', 'created_at')
#     search_fields = ('id', 'name', 'created_at')
#     list_filter = ('created_at',)
#
#
# @admin.register(Tag)
# class TagAdmin(admin.ModelAdmin):
#     list_display = ('id', 'name', 'group', 'created_at')
#     search_fields = ('id', 'name', 'group__name', 'group__id')
#     list_filter = ('created_at',)
#
#
# @admin.register(Product)
# class ProductAdmin(admin.ModelAdmin):
#     inlines = [ProductImageInline]
#     list_display = ('id', 'name', 'site_price', 'price', 'is_active', 'availability', 'created_at')
#     list_display_links = ('id', 'name')
#     search_fields = ('id', 'name')
#     search_help_text = _('Search by fields: ID, Rakuten ID, NAME, GENRE NAME')
#     list_filter = ('is_active', 'created_at', 'modified_at')
#     readonly_fields = ('id', 'created_at', 'modified_at', 'genres', 'tags')
#     fieldsets = (
#         (
#             _('General Info'),
#             {'fields': ('id', 'name', 'description', 'rakuten_price', 'increase_percentage', 'genres', 'tags')}
#         ),
#         (_('Dates'), {'classes': ['collapse'], 'fields': ('created_at', 'modified_at')}),
#         (_('Control'), {'fields': ('availability', 'is_active')}),
#         (_('Links'), {'classes': ['collapse'], 'fields': ('product_url',)})
#     )
#     list_per_page = 30
#     list_max_show_all = 50
#
#
# @admin.register(ProductReview)
# class ProductReview(admin.ModelAdmin):
#     list_display = ('id', 'product', 'user', 'rank', 'is_active', 'created_at')
#     list_display_links = ('id', 'product', 'user')
#     search_fields = ('id', 'product_id', 'user__email')
#     list_filter = ('is_active', 'created_at')
#     readonly_fields = ('created_at', 'modified_at',)
