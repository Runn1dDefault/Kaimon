# Generated by Django 4.2.4 on 2023-12-18 09:58

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0003_paymenttransactionreceipt_and_add_order_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymenttransactionreceipt',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, unique=True),
        ),
    ]
