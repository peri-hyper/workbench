# Generated by Django 4.2.13 on 2025-05-21 08:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0073_remarkstemplatetable'),
    ]

    operations = [
        migrations.AlterField(
            model_name='purchasetable',
            name='remark',
            field=models.CharField(blank=True, max_length=5000, null=True, verbose_name='备注'),
        ),
        migrations.AlterField(
            model_name='remarkstemplatetable',
            name='creat_date',
            field=models.DateField(auto_now_add=True, verbose_name='创建日期'),
        ),
    ]
