# Generated by Django 4.2.13 on 2025-03-18 03:09

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0045_inspectioncuttingrecord'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='inspectioncuttingrecord',
            name='general_tolerance',
        ),
        migrations.AlterModelTable(
            name='inspectioncuttingrecord',
            table='inspection_cutting_record_tb',
        ),
    ]
