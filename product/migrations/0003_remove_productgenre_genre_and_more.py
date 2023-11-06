# Generated by Django 4.2.4 on 2023-11-01 20:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0002_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='genre',
            name='name_en',
        ),
        migrations.RemoveField(
            model_name='genre',
            name='name_ky',
        ),
        migrations.RemoveField(
            model_name='genre',
            name='name_kz',
        ),
        migrations.RemoveField(
            model_name='genre',
            name='name_ru',
        ),
        migrations.RemoveField(
            model_name='genre',
            name='name_tr',
        ),
        migrations.RemoveField(
            model_name='product',
            name='description_en',
        ),
        migrations.RemoveField(
            model_name='product',
            name='description_ky',
        ),
        migrations.RemoveField(
            model_name='product',
            name='description_kz',
        ),
        migrations.RemoveField(
            model_name='product',
            name='description_ru',
        ),
        migrations.RemoveField(
            model_name='product',
            name='description_tr',
        ),
        migrations.RemoveField(
            model_name='product',
            name='name_en',
        ),
        migrations.RemoveField(
            model_name='product',
            name='name_ky',
        ),
        migrations.RemoveField(
            model_name='product',
            name='name_kz',
        ),
        migrations.RemoveField(
            model_name='product',
            name='name_ru',
        ),
        migrations.RemoveField(
            model_name='product',
            name='name_tr',
        ),
        migrations.RemoveField(
            model_name='product',
            name='price',
        ),
        migrations.RemoveField(
            model_name='product',
            name='reference_rank',
        ),
        migrations.RemoveField(
            model_name='tag',
            name='name_en',
        ),
        migrations.RemoveField(
            model_name='tag',
            name='name_ky',
        ),
        migrations.RemoveField(
            model_name='tag',
            name='name_kz',
        ),
        migrations.RemoveField(
            model_name='tag',
            name='name_ru',
        ),
        migrations.RemoveField(
            model_name='tag',
            name='name_tr',
        ),
        migrations.RemoveField(
            model_name='taggroup',
            name='name_en',
        ),
        migrations.RemoveField(
            model_name='taggroup',
            name='name_ky',
        ),
        migrations.RemoveField(
            model_name='taggroup',
            name='name_kz',
        ),
        migrations.RemoveField(
            model_name='taggroup',
            name='name_ru',
        ),
        migrations.RemoveField(
            model_name='taggroup',
            name='name_tr',
        ),
        migrations.AlterField(
            model_name='genre',
            name='name',
            field=models.CharField(default='deleted', max_length=100),
            preserve_default=False,
        ),
        migrations.AddIndex(
            model_name='genre',
            index=models.Index(condition=models.Q(('level', 0), _negated=True), fields=['name'], include=('level',), name='exclude_zero_idx'),
        ),
        migrations.AddIndex(
            model_name='genre',
            index=models.Index(condition=models.Q(('deactivated', False)), fields=['name'], include=('deactivated',), name='activate_genres_idx'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['avg_rank'], name='product_pro_avg_ran_e104bf_idx'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['created_at'], name='product_pro_created_57e07a_idx'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['reviews_count'], name='product_pro_reviews_217c03_idx'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['receipts_qty'], name='product_pro_receipt_93c21c_idx'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(condition=models.Q(('availability', True)), fields=['name'], include=('availability',), name='available_idx'),
        ),
        migrations.AddIndex(
            model_name='productimageurl',
            index=models.Index(fields=['product', 'url'], name='product_pro_product_02611d_idx'),
        ),
        migrations.AddField(
            model_name='product',
            name='genres',
            field=models.ManyToManyField(db_table='product_product_genres', related_name='products',
                                         to='product.genre'),
        ),
        migrations.AddField(
            model_name='product',
            name='tags',
            field=models.ManyToManyField(db_table='product_product_tags', related_name='products', to='product.tag'),
        )
    ]