# Generated by Django 4.2.4 on 2023-12-16 12:52
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0002_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PaymentTransactionReceipt',
            fields=[
                ('order', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to='orders.order')),
                ('payment_id', models.CharField(max_length=100, unique=True)),
                ('redirect_url', models.URLField(blank=True, max_length=700, null=True)),
                ('send_amount', models.DecimalField(decimal_places=10, max_digits=20)),
                ('receive_amount', models.DecimalField(decimal_places=10, max_digits=20)),
                ('receive_currency', models.CharField(blank=True, max_length=10, null=True)),
                ('clearing_amount', models.DecimalField(decimal_places=10, max_digits=20, null=True)),
                ('card_name', models.CharField(blank=True, max_length=255, null=True)),
                ('card_pan', models.CharField(blank=True, max_length=20, null=True)),
                ('auth_code', models.CharField(blank=True, max_length=100, null=True)),
                ('reference', models.CharField(blank=True, max_length=100, null=True)),
                ('initialized_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(choices=[('wait_payment', 'Wait Payment'), ('payment_rejected', 'Payment Rejected'),
                                            ('pending', 'Pending'), ('in_process', 'In Process'),
                                            ('in_delivering', 'In Delivering'), ('success', 'Success')],
                                   default='wait_payment', max_length=20),
        ),
    ]
