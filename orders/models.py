from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from products.models import Product, Tag
from service.models import Currencies
from users.utils import get_sentinel_user

from .validators import only_digit_validator
from .querysets import OrderAnalyticsQuerySet


class BaseModel(models.Model):
    objects = models.Manager()
    id = models.UUIDField(primary_key=True, default=uuid4)

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
    bayer_code = models.CharField(max_length=50, unique=True)
    email = models.EmailField()
    phone = models.CharField(max_length=20, validators=[only_digit_validator])

    def __str__(self):
        return self.name

    # @property
    # def bayer_code(self):
    #     name_symbols = ''.join([i[0].title() for i in getattr(self, 'name').split()])
    #     return f"{name_symbols}{self.id}"


class DeliveryAddress(BaseModel):
    objects = models.Manager()

    class CountryCode(models.TextChoices):
        KG = 'KG', _('Kyrgyzstan')
        KZ = 'KZ', _('Kazahstan')
        UZ = 'UZ', _('Uzbekistan')
        TG = 'TG', _('Tajikistan')

    user = models.ForeignKey(get_user_model(), on_delete=models.SET(get_sentinel_user),
                             related_name='delivery_addresses')
    recipient_name = models.CharField(max_length=100)
    country_code = models.CharField(max_length=5, choices=CountryCode.choices, default=CountryCode.KG)
    city = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20, null=True, blank=True)
    address_line = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = _('Delivery Address')
        verbose_name_plural = _('Delivery Addresses')

    def __str__(self):
        return f"{self.recipient_name} ({self.country_code})"


class Order(BaseModel):
    objects = models.Manager()
    analytics = OrderAnalyticsQuerySet.as_manager()

    class Status(models.TextChoices):
        wait_payment = 'wait_payment', _('Wait Payment')
        pending = 'pending', _('Pending')
        in_process = 'in_process', _('In Process')
        in_delivering = 'in_delivering', _('In Delivering')
        success = 'success', _('Success')

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='orders')
    delivery_address = models.ForeignKey(DeliveryAddress, on_delete=models.RESTRICT, related_name='orders')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.wait_payment)
    comment = models.TextField(null=True, blank=True)

    @property
    def bayer_code(self):
        return getattr(self.customer, 'bayer_code')

    @property
    def phone(self):
        return getattr(self.customer, 'phone', None)


class OrderShipping(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, primary_key=True, related_name='shipping_detail')
    shipping_carrier = models.CharField(max_length=50, default='FedEx')
    shipping_weight = models.IntegerField(verbose_name=_('Shipping weight'), blank=True, null=True)
    qrcode_image = models.ImageField(upload_to='qrcodes/', blank=True, null=True)
    total_price = models.DecimalField(max_digits=20, decimal_places=10)


class OrderConversion(models.Model):
    objects = models.Manager()

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='conversions')
    currency = models.CharField(max_length=5, choices=Currencies.choices)
    price_per = models.DecimalField(max_digits=20, decimal_places=10)


def get_sentinel_product():
    product, _ = Product.objects.get_or_create(
        id='deleted_product',
        name='deleted',
        site_price=0,
    )
    if product.is_active:
        product.is_active = False
        product.save()
    return product


class Receipt(BaseModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='receipts')
    product = models.ForeignKey(Product, on_delete=models.SET(get_sentinel_product), related_name='receipts')
    product_name = models.CharField(max_length=255)
    product_image = models.TextField(blank=True, null=True)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)], default=1)
    unit_price = models.DecimalField(max_digits=20, decimal_places=10)
    site_price = models.DecimalField(max_digits=20, decimal_places=10)
    site_currency = models.CharField(max_length=5, choices=Currencies.choices)
    discount = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=0
    )
    avg_weight = models.FloatField()
    tags = models.ManyToManyField(Tag, blank=True)

    @property
    def total_price(self):
        discount = getattr(self, 'discount')
        unit_price = getattr(self, 'unit_price')
        if discount > 0:
            unit_price -= (unit_price * discount) / 100
        return unit_price * self.quantity

    @property
    def sale_unit_price(self):
        discount = getattr(self, 'discount')
        unit_price = getattr(self, 'unit_price')
        if discount <= 0:
            return unit_price
        return unit_price - (unit_price * discount) / 100
