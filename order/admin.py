from django.contrib import admin

from .models import DeliveryAddress, Order, OrderReceipt


@admin.register(DeliveryAddress)
class DeliveryAddressAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'country', 'city', 'as_deleted', 'created_at')
    search_fields = ('id', 'user__email', 'city', 'country__name',)
    list_filter = ('as_deleted', 'created_at',)
    readonly_fields = ('created_at',)


class OrderReceiptInline(admin.StackedInline):
    model = OrderReceipt
    extra = 0
    fieldsets = (
        (
            'R...', {
                'classes': ['collapse'],
                'fields': ('product', 'unit_price', 'discount', 'quantity', 'tags')
            }
        ),
    )


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    inlines = [OrderReceiptInline]
    list_display = ('id', 'delivery_address', 'status', 'created_at')
    list_display_links = ('id', 'delivery_address')
    search_fields = ('id', 'customer__email', 'customer__phone', 'delivery_address_id')
    list_filter = ('status', 'created_at')
    readonly_fields = ('created_at', 'modified_at')
