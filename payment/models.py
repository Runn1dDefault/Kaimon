# from django.contrib.auth import get_user_model
# from django.db import models
# from django.utils.translation import gettext_lazy as _
#
# from users.utils import get_sentinel_user
#
#
# class Payment(models.Model):
#     class Type(models.TextChoices):
#         order = 'order', _('Order')
#         service = 'service', _('Service')
#
#     user = models.ForeignKey(get_user_model(), on_delete=models.SET(get_sentinel_user), related_name='payments',
#                              null=True)
#     payment_type = models.CharField(choices=Type.choices, max_length=10)
#     amount_paid = models.FloatField()
#     payment_date = models.DateTimeField(auto_now_add=True)
#
#     def __str__(self):
#         return f"Payment for Order {self.order.pk}"
