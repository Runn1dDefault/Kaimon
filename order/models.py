from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from product.models import Product


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Country(BaseModel):
    name = models.CharField(max_length=100, verbose_name=_('Name') + '[ja]', unique=True)
    name_tr = models.CharField(max_length=100, blank=True, null=True, verbose_name=_('Name') + '[tr]')
    name_ru = models.CharField(max_length=100, blank=True, null=True, verbose_name=_('Name') + '[ru]')
    name_en = models.CharField(max_length=100, blank=True, null=True, verbose_name=_('Name') + '[en]')
    name_ky = models.CharField(max_length=100, blank=True, null=True, verbose_name=_('Name') + '[ky]')
    name_kz = models.CharField(max_length=100, blank=True, null=True, verbose_name=_('Name') + '[kz]')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = _('Countries')


class UserDeliveryAddress(BaseModel):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='delivery_addresses')
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='delivery_addresses')
    city = models.CharField(max_length=255)
    address = models.TextField()
    phone = models.CharField(max_length=15)
    zip_code = models.CharField(max_length=50, blank=True, null=True)

    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.user.email}'

    class Meta:
        verbose_name = _('Delivery Address')
        verbose_name_plural = _('Delivery Addresses')


class Order(BaseModel):
    class Status(models.TextChoices):
        pending = 'pending', _('Pending')
        rejected = 'rejected', _('Rejected')
        canceled = 'canceled', _('Canceled')
        delivered = 'delivered', _('Delivered')
        success = 'success', _('Success')

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.pending)
    delivery_address = models.ForeignKey(UserDeliveryAddress, on_delete=models.CASCADE, related_name='orders')
    is_deleted = models.BooleanField(default=False)
    is_payed = models.BooleanField(default=False)

    def delete_receipts(self):
        if self.status == self.Status.pending:
            return

        receipts = self.receipts.filter(is_canceled=False)
        for receipt in receipts:
            receipt.is_canceled = True
            receipt.returns = receipt.total_qty
            receipt.qty = 0
        self.__class__.objects.bulk_update(receipts, {'is_canceled', 'returns', 'qty'})


class ProductReceipt(BaseModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='receipts')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, related_name='receipts', blank=True, null=True)
    p_id = models.BigIntegerField()
    product_name = models.CharField(max_length=500)
    image_url = models.TextField(blank=True, null=True)
    unit_price = models.FloatField()
    total_qty = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    qty = models.PositiveIntegerField(validators=[MinValueValidator(0)])
    returns = models.PositiveIntegerField(default=0)
    is_canceled = models.BooleanField(default=False)
