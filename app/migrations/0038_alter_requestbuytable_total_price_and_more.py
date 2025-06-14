# Generated by Django 4.2.13 on 2024-08-29 09:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0037_alter_ordertable_shpping_date'),
    ]

    operations = [
        migrations.AlterField(
            model_name='requestbuytable',
            name='total_price',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='总价'),
        ),
        migrations.AlterField(
            model_name='requestbuytable',
            name='unit_price',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='单价'),
        ),
    ]
