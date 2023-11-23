from django.contrib import admin

from .models import Customer, DeliveryAddress, Order, Receipt


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'email')
    search_fields = ('id', 'name', 'email')


@admin.register(DeliveryAddress)
class DeliveryAddressAdmin(admin.ModelAdmin):
    autocomplete_fields = ('user',)
    list_display = ('id', 'user', 'country_code', 'postal_code')
    search_fields = ('id', 'user__email', 'postal_code',)
    list_filter = ('created_at', 'country_code')
    readonly_fields = ('created_at', 'modified_at')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    autocomplete_fields = ('customer', 'delivery_address')
    list_display = ('id', 'delivery_address', 'status', 'created_at')
    list_display_links = ('id', 'delivery_address')
    search_fields = ('id', 'customer__email', 'customer__phone', 'delivery_address_id')
    list_filter = ('status', 'created_at')
    readonly_fields = ('created_at', 'modified_at')


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    autocomplete_fields = ('order', 'product', 'tags',)
    list_display = ('id', 'order', 'product')
    search_fields = ('id', 'order_id', 'product_id')