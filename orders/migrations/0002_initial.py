# Generated by Django 4.2.4 on 2023-11-26 15:22

from django.conf import settings
from django.db import migrations, models
import users.utils


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('orders', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='deliveryaddress',
            name='user',
            field=models.ForeignKey(on_delete=models.SET(users.utils.get_sentinel_user), related_name='delivery_addresses', to=settings.AUTH_USER_MODEL),
        ),
    ]
