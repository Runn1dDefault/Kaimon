# Generated by Django 4.2.4 on 2023-12-20 13:17
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0004_paymenttransactionreceipt_uuid_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='paymenttransactionreceipt',
            name='receive_amount',
            field=models.DecimalField(decimal_places=10, max_digits=20, null=True),
        ),
        migrations.AlterField(
            model_name='paymenttransactionreceipt',
            name='order',
            field=models.OneToOneField(on_delete=models.deletion.CASCADE, primary_key=True,
                                       related_name='payment_transaction', serialize=False, to='orders.order'),
        ),
    ]