# Generated by Django 4.2.4 on 2024-02-21 14:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('promotions', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='promotion',
            name='site',
            field=models.CharField(choices=[('rakuten', 'rakuten'), ('uniqlo', 'uniqlo'), ('kaimono', 'kaimono')], default=1),
            preserve_default=False,
        ),
    ]
