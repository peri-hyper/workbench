# Generated by Django 4.2.13 on 2024-07-31 10:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0024_filetable_customer_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='inventorytable',
            name='material_type',
            field=models.CharField(max_length=5, verbose_name='类型'),
        ),
    ]
