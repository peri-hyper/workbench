# Generated by Django 4.2.13 on 2025-03-19 03:10

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0046_remove_inspectioncuttingrecord_general_tolerance_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='InspectionCuttingDetailRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('checkpoint', models.IntegerField(verbose_name='检查点')),
                ('required_value', models.FloatField(verbose_name='要求值')),
                ('tolerance', models.CharField(max_length=50, verbose_name='公差')),
                ('actual_value', models.FloatField(verbose_name='实际值')),
                ('image_1', models.ImageField(blank=True, null=True, upload_to='images/reference_image/', verbose_name='图片1')),
                ('image_2', models.ImageField(blank=True, null=True, upload_to='images/reference_image/', verbose_name='图片2')),
                ('image_3', models.ImageField(blank=True, null=True, upload_to='images/reference_image/', verbose_name='图片3')),
                ('inspection_number', models.CharField(max_length=50, unique=True, verbose_name='检验单号')),
                ('pointX', models.FloatField(verbose_name='X 坐标')),
                ('pointY', models.FloatField(verbose_name='Y 坐标')),
            ],
            options={
                'db_table': 'inspection_cutting_record_detail_tb',
            },
        ),
        migrations.AddField(
            model_name='inspectioncuttingrecord',
            name='customer_name',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='app.customertable', to_field='customer_name', verbose_name='客户名称'),
            preserve_default=False,
        ),
    ]
