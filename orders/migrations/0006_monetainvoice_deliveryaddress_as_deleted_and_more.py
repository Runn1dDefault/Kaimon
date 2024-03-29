# Generated by Django 4.2.4 on 2024-02-21 14:28

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0005_paymenttransactionreceipt_receive_amount_nullable'),
    ]

    operations = [
        migrations.CreateModel(
            name='MonetaInvoice',
            fields=[
                ('order', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name='moneta_invoice', serialize=False, to='orders.order')),
                ('invoice_id', models.CharField(max_length=100)),
                ('address', models.CharField(max_length=100)),
                ('signer', models.CharField(max_length=100)),
                ('currency', models.CharField(max_length=20)),
                ('payment_link', models.URLField(max_length=700)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=20)),
                ('expired', models.DateTimeField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.AlterField(
            model_name='orderconversion',
            name='currency_from',
            field=models.CharField(choices=[('usd', 'Dollar'), ('som', 'Som'), ('yen', 'Yen'), ('moneta', 'Moneta')], max_length=10),
        ),
        migrations.AlterField(
            model_name='orderconversion',
            name='currency_to',
            field=models.CharField(choices=[('usd', 'Dollar'), ('som', 'Som'), ('yen', 'Yen'), ('moneta', 'Moneta')], max_length=10),
        ),
        migrations.AlterField(
            model_name='orderconversion',
            name='price_per',
            field=models.DecimalField(decimal_places=2, max_digits=20),
        ),
        migrations.AlterField(
            model_name='paymenttransactionreceipt',
            name='clearing_amount',
            field=models.DecimalField(decimal_places=2, max_digits=20, null=True),
        ),
        migrations.AlterField(
            model_name='paymenttransactionreceipt',
            name='receive_amount',
            field=models.DecimalField(decimal_places=2, max_digits=20, null=True),
        ),
        migrations.AlterField(
            model_name='paymenttransactionreceipt',
            name='send_amount',
            field=models.DecimalField(decimal_places=2, max_digits=20),
        ),
        migrations.AlterField(
            model_name='receipt',
            name='site_currency',
            field=models.CharField(choices=[('usd', 'Dollar'), ('som', 'Som'), ('yen', 'Yen'), ('moneta', 'Moneta')], max_length=10),
        ),
        migrations.AlterField(
            model_name='receipt',
            name='site_price',
            field=models.DecimalField(decimal_places=2, max_digits=20),
        ),
        migrations.AlterField(
            model_name='receipt',
            name='unit_price',
            field=models.DecimalField(decimal_places=2, max_digits=20),
        ),
    ]
