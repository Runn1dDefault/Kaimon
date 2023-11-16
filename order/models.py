from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from users.utils import get_sentinel_user

from .validators import only_digit_validator
from .querysets import OrderAnalyticsQuerySet


class BaseModel(models.Model):
    objects = models.Manager()

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Customer(BaseModel):
    """
    model for saving recipient data for history and analytics
    """
    objects = models.Manager()

    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, validators=[only_digit_validator])

    def __str__(self):
        return self.name


class DeliveryAddress(BaseModel):
    objects = models.Manager()

    class CountryCode(models.TextChoices):
        JP = 'JP', _('Japanese')
        KG = 'KG', _('Kyrgyzstan')
        KZ = 'KZ', _('Kazahstan')
        TR = 'TR', _('Türkiye')
        RU = 'RU', _('Russia')

    user = models.ForeignKey(get_user_model(), on_delete=models.SET(get_sentinel_user),
                             related_name='delivery_addresses')
    recipient_name = models.CharField(max_length=100)
    country_code = models.CharField(choices=CountryCode.choices, default=CountryCode.KG)
    city = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20, null=True, blank=True)
    address_line = models.TextField(blank=True, null=True)
    as_deleted = models.BooleanField(default=False)

    class Meta:
        verbose_name = _('Delivery Address')
        verbose_name_plural = _('Delivery Addresses')


class Order(BaseModel):
    objects = models.Manager()
    analytics = OrderAnalyticsQuerySet.as_manager()

    class Status(models.TextChoices):
        pending = 'pending', _('Pending')
        rejected = 'rejected', _('Rejected')
        in_process = 'in_process', _('In Process')
        in_delivering = 'in_delivering', _('In Delivering')
        success = 'success', _('Success')

    customer = models.ForeignKey(Customer, on_delete=models.RESTRICT, related_name='orders')
    delivery_address = models.ForeignKey(DeliveryAddress, on_delete=models.RESTRICT, related_name='orders')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.pending)
    comment = models.TextField(null=True, blank=True)

    # important!: when updating an address, create a new address and mark the old one as deleted
    shipping_carrier = models.CharField(max_length=50, default='FedEx')
    shipping_weight = models.IntegerField(verbose_name=_('Shipping weight'), blank=True, null=True)
    barcode = models.ImageField(upload_to='order/barcodes/')

    # for correct analytics, the value of conversions for two currencies with yen will be saved here
    yen_to_usd = models.DecimalField(max_digits=20, decimal_places=10)
    yen_to_som = models.DecimalField(max_digits=20, decimal_places=10)

    @property
    def phone(self):
        return getattr(self.customer, 'phone', None)

    @property
    def total_prices(self):
        receipts = getattr(self, 'receipts')
        if not receipts.exists():
            return 0.0
        order_id = getattr(self, 'id')
        return self.__class__.analytics.filter(id=order_id).total_prices().values()[0]


class Receipt(BaseModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='receipts')
    product = models.ForeignKey('product.Product', on_delete=models.RESTRICT, related_name='receipts')
    unit_price = models.DecimalField(max_digits=20, decimal_places=10)
    discount = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)], default=1)


class ReceiptTag(models.Model):
    objects = models.Manager()

    receipt = models.ForeignKey(Receipt, on_delete=models.CASCADE, related_name='tags')
    tag = models.ForeignKey('product.Tag', on_delete=models.RESTRICT)
