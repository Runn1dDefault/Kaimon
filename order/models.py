from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from order.querysets import OrderAnalyticsQuerySet
from order.validators import only_digit_validator
from product.models import Product, Tag
from users.utils import get_sentinel_user


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
    user = models.ForeignKey(get_user_model(), on_delete=models.SET(get_sentinel_user),
                             related_name='delivery_addresses')
    recipient_name = models.CharField(max_length=100)
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)

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
        canceled = 'canceled', _('Canceled')
        delivered = 'delivered', _('Delivered')
        success = 'success', _('Success')

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='delivery_addresses')
    delivery_address = models.ForeignKey(DeliveryAddress, on_delete=models.RESTRICT, related_name='orders')
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.pending)
    # important!: when updating an address, create a new address and mark the old one as deleted
    shipping_carrier = models.CharField(max_length=50, default='FedEx')
    shipping_weight = models.IntegerField(verbose_name=_('Shipping weight'), blank=True, null=True)
    comment = models.TextField(null=True, blank=True)
    # for correct analytics, the value of conversions for two currencies with yen will be saved here
    yen_to_usd = models.FloatField()
    yen_to_som = models.FloatField()


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
