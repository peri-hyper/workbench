# Generated by Django 4.2.13 on 2024-08-30 08:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0040_alter_purchasedetailtable_total_price_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='outwarddetail',
            name='total_price',
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=10, null=True, verbose_name='总价'),
        ),
        migrations.AlterField(
            model_name='outwarddetail',
            name='unit_price',
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=10, null=True, verbose_name='单价'),
        ),
        migrations.AlterField(
            model_name='purchasedetailtable',
            name='total_price',
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=10, null=True, verbose_name='总价'),
        ),
        migrations.AlterField(
            model_name='purchasedetailtable',
            name='unit_price',
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=10, null=True, verbose_name='单价'),
        ),
    ]
