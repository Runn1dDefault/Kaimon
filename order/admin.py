from django.contrib import admin

from .models import Customer, DeliveryAddress, Order, Receipt, ReceiptTag


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'email')
    search_fields = ('id', 'name', 'email')


@admin.register(DeliveryAddress)
class DeliveryAddressAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'country', 'city', 'state', 'as_deleted', 'created_at')
    search_fields = ('id', 'user__email', 'country',  'city',)
    list_filter = ('as_deleted', 'created_at', 'country', 'state')
    readonly_fields = ('created_at',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'delivery_address', 'status', 'created_at')
    list_display_links = ('id', 'delivery_address')
    search_fields = ('id', 'customer__email', 'customer__phone', 'delivery_address_id')
    list_filter = ('status', 'created_at')
    readonly_fields = ('created_at', 'modified_at')


@admin.register(ReceiptTag)
class ReceiptTagAdmin(admin.ModelAdmin):
    pass


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'product')
    search_fields = ('id', 'order_id', 'product_id')
