from django.contrib import admin

from .models import Customer, DeliveryAddress, Order, OrderConversion, OrderShipping, Receipt, Payment


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


class OrderConversionInline(admin.StackedInline):
    model = OrderConversion
    extra = 1


class OrderShippingDetailInline(admin.StackedInline):
    model = OrderShipping
    extra = 1


class PaymentInline(admin.StackedInline):
    model = Payment
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    inlines = [OrderConversionInline, OrderShippingDetailInline, PaymentInline]
    autocomplete_fields = ('customer', 'delivery_address')
    list_display = ('id', 'delivery_address', 'status', 'created_at')
    list_display_links = ('id', 'delivery_address')
    search_fields = ('id', 'customer__email', 'customer__name', 'delivery_address_id')
    list_filter = ('status', 'created_at')
    readonly_fields = ('id', 'created_at', 'modified_at')


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    autocomplete_fields = ('order',)
    list_display = ('id', 'order', 'product_code')
    search_fields = ('id', 'order_id', 'product_code', "product_name", "shop_code")
    readonly_fields = ("id",)
