# Generated by Django 4.2.13 on 2024-07-28 07:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0017_shippingdetailtable_shipping_weight'),
    ]

    operations = [
        migrations.AlterField(
            model_name='productionprocesstable',
            name='processid',
            field=models.BigAutoField(primary_key=True, serialize=False, verbose_name='主键'),
        ),
    ]
