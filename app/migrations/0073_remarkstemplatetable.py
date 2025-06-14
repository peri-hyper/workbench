# Generated by Django 4.2.13 on 2025-05-20 09:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0072_incominginspectiondetail_inspection_number'),
    ]

    operations = [
        migrations.CreateModel(
            name='RemarksTemplateTable',
            fields=[
                ('templateid', models.AutoField(primary_key=True, serialize=False, verbose_name='主键')),
                ('template_name', models.CharField(max_length=30, verbose_name='模版名称')),
                ('creat_date', models.DateField(verbose_name='创建日期')),
                ('creat_user', models.CharField(max_length=10, verbose_name='领料人')),
                ('remarks_data', models.CharField(max_length=5000, verbose_name='内容')),
            ],
            options={
                'db_table': 'remarks_template_tb',
            },
        ),
    ]
