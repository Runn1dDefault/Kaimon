from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from order.querysets import OrderAnalyticsQuerySet
from order.validators import only_digit_validator
from product.models import Product, Tag


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Customer(BaseModel):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, validators=[only_digit_validator])

    def __str__(self):
        return self.name


class DeliveryAddress(BaseModel):
    customer = models.ForeignKey(Customer, on_delete=models.RESTRICT, related_name='delivery_addresses')
    recipient_name = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    state = models.CharField(max_length=100, blank=True, null=True)
    address_line = models.TextField(blank=True, null=True)

    as_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.recipient_name}'s Address"

    class Meta:
        verbose_name = _('Delivery Address')
        verbose_name_plural = _('Delivery Addresses')


class Order(BaseModel):
    objects = models.Manager()
    analytics = OrderAnalyticsQuerySet.as_manager()

    class Status(models.TextChoices):
        pending = 'pending', _('Pending')
        rejected = 'rejected', _('Rejected')
        delivered = 'delivered', _('Delivered')
        success = 'success', _('Success')

    delivery_address = models.ForeignKey(DeliveryAddress, on_delete=models.RESTRICT, related_name='orders')
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.pending)
    comment = models.TextField(null=True, blank=True)

    # important!: when updating an address, create a new address and mark the old one as deleted
    shipping_carrier = models.CharField(max_length=50, default='FedEx')
    shipping_weight = models.IntegerField(verbose_name=_('Shipping weight'), blank=True, null=True)
    # for correct analytics, the value of conversions for two currencies with yen will be saved here
    yen_to_usd = models.FloatField()
    yen_to_som = models.FloatField()

    @property
    def total_price(self):
        if not self.receipts.exists():
            return 0.0

        sale_price_case = self.__class__.analytics.sale_price_case(from_receipts=True)
        receipts_prices = self.receipts.annotate(receipt_price=sale_price_case).values_list('receipt_price', flat=True)
        return sum(list(receipts_prices))


class OrderReceipt(BaseModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='receipts')
    product = models.ForeignKey(Product, on_delete=models.RESTRICT, related_name='receipts')
    unit_price = models.FloatField()
    discount = models.FloatField(default=0.0)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)], default=1)
    # product tags of client choice will be saved in field tags,
    # for a better understanding of what the client wants to order
    tags = models.ManyToManyField(
        Tag,
        blank=True,
        related_name='receipts'
    )
