from django.contrib import admin
from django.template.defaultfilters import truncatechars
from django.utils.translation import gettext_lazy as _

from .models import Site, Category, Tag, Product, ProductImage, ProductInventory, ProductReview


class SiteFilter(admin.SimpleListFilter):
    title = 'Site Filter'
    parameter_name = 'site'

    def lookups(self, request, model_admin):
        return ((site.value, site.value.title()) for site in Site)

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(id__startswith=self.value())
        return queryset


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    autocomplete_fields = ("parent",)
    search_fields = ("id", "name",)
    list_display = ("id", "name", "level", "deactivated")
    list_filter = (SiteFilter, "level", "deactivated")
    list_per_page = 15

    def get_search_results(self, request, queryset, search_term):
        referer = request.META.get('HTTP_REFERER')
        if not referer:
            return super().get_search_results(request, queryset, search_term)

        model_name = request.GET.get('model_name')
        instance_id = referer.split('/')[-3].replace('_5F', '_')
        site = instance_id.split("_")[0]

        try:
            Site.from_string(site)
        except KeyError:
            return super().get_search_results(request, queryset, search_term)
        else:
            queryset = queryset.filter(id__startswith=site)
            if model_name == 'category':
                queryset = queryset.filter(level__lt=Category.objects.get(id=instance_id).level)
            return super().get_search_results(request, queryset, search_term)


class GroupFilter(admin.SimpleListFilter):
    title = "Group Filter"
    parameter_name = "is_group"

    def lookups(self, request, model_admin):
        return (
            ("yes", _("Yes")),
            ("no", _("No"))
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == "yes":
            return queryset.filter(group__isnull=True)
        elif value == "no":
            return queryset.filter(group__isnull=False)
        return queryset


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    autocomplete_fields = ("group",)
    list_display = ("id", "name", "is_group")
    list_filter = (SiteFilter, GroupFilter)
    search_fields = ("id", "name")
    list_per_page = 15

    @admin.display(description='Is group', boolean=True)
    def is_group(self, obj) -> bool:
        return not (obj.group is not None)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        site = request.path.split('/')[-3].split('_')[0]
        if db_field.name == 'group':
            kwargs['queryset'] = Tag.objects.query_by_site(site=site).filter(group_id__isnull=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class ProductImageInline(admin.TabularInline):
    verbose_name = "Image"
    verbose_name_plural = "Images"
    model = ProductImage
    extra = 0
    min_num = 1
    classes = ("collapse",)


class ProductInventoryInline(admin.StackedInline):
    verbose_name = "Inventory"
    verbose_name_plural = "Inventories"
    model = ProductInventory
    extra = 0
    classes = ("collapse",)


class HasReviewFilter(admin.SimpleListFilter):
    title = "Review Filter"
    parameter_name = "has_reviews"

    def lookups(self, request, model_admin):
        return (
            ("yes", _("Yes")),
            ("no", _("No"))
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == "yes":
            return queryset.filter(reviews__isnull=False)
        elif value == "no":
            return queryset.filter(reviews__isnull=True)
        return queryset


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductImageInline, ProductInventoryInline]
    autocomplete_fields = ("categories", "tags")
    list_display = ("id", 'product_name', "product_price", "is_active", "created_at")
    search_fields = ("id", "name")
    list_filter = (SiteFilter, "is_active", "modified_at", HasReviewFilter, "site_avg_rating",)
    list_per_page = 15
    readonly_fields = ("created_at", "modified_at")

    fieldsets = (
        (
            _('Product Info'),
            {'fields': ('id', 'name', 'description', 'site_price', 'increase_per', 'is_active')}
        ),
        (
            _('Dates'),
            {'fields': ('created_at', 'modified_at')}
        ),
        (
            _("Relations"),
            {'classes': ['collapse'], 'fields': ('categories', 'tags')}
        )
    )

    def product_name(self, obj):
        return truncatechars(obj.name, 35)

    product_name.admin_order_field = 'name'
    product_name.short_description = _('Product Name')

    def product_price(self, obj):
        return float(obj.price)

    product_price.admin_order_field = 'site_price'
    product_price.short_description = _('Price')


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    autocomplete_fields = ('user', 'product')
    list_display = ('id', 'user', 'product_id', 'short_comment', 'moderated', 'is_read')
    list_display_links = ('id', 'user', 'product_id')
    search_fields = ('id', 'user__email', 'user__full_name')
    list_filter = ('rating', 'created_at', 'is_read', 'moderated')

    def product_id(self, obj):
        return obj.product.id

    product_id.admin_order_field = 'product'
    product_id.short_description = _('Product ID')

    def short_comment(self, obj):
        return truncatechars(obj.comment, 35)

    short_comment.admin_order_field = 'comment'
    short_comment.short_description = _('Comment')
