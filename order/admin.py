from django.contrib import admin

from .models import Country, UserDeliveryAddress, Order, ProductReceipt


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'is_active', 'created_at')
    list_display_links = ('id', 'name', 'is_active')
    search_fields = ('id', 'name', 'name_tr', 'name_ru', 'name_en', 'name_ky', 'name_kz')
    list_filter = ('is_active', 'created_at')
    readonly_fields = ('created_at', 'modified_at')


@admin.register(UserDeliveryAddress)
class UserDeliveryAddressAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'country', 'city', 'is_deleted', 'created_at')
    search_fields = ('id', 'user__email', 'city', 'country__name', 'country__name_ru',
                     'country__name_en', 'country__name_ky', 'country__name_kz')
    list_filter = ('is_deleted', 'created_at')
    readonly_fields = ('created_at', 'modified_at')


class ProductReceiptInline(admin.StackedInline):
    model = ProductReceipt
    extra = 1
    fieldsets = (
        (
            'R...', {
                'classes': ['collapse'],
                'fields': ('name', 'status', 'delivery_address', 'is_deleted', 'is_payed')
            }
        ),
    )


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    inlines = [ProductReceiptInline]
    list_display = ('id', 'status', 'is_deleted', 'delivery_address', 'created_at')
    search_fields = ('id', 'is_deleted')
    list_filter = ('is_deleted', 'status', 'created_at')
    readonly_fields = ('created_at', 'modified_at')
