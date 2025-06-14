# Generated by Django 4.2.13 on 2025-04-27 07:19

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0068_incominginspectionrecord_incominginspectiondetail'),
    ]

    operations = [
        migrations.AddField(
            model_name='incominginspectiondetail',
            name='inspection_number',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='app.incominginspectionrecord', verbose_name='检验单号'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='incominginspectiondetail',
            name='image1',
            field=models.ImageField(blank=True, null=True, upload_to='images/reference_image/', verbose_name='图片1'),
        ),
        migrations.AlterField(
            model_name='incominginspectiondetail',
            name='image2',
            field=models.ImageField(blank=True, null=True, upload_to='images/reference_image/', verbose_name='图片2'),
        ),
        migrations.AlterField(
            model_name='incominginspectiondetail',
            name='image3',
            field=models.ImageField(blank=True, null=True, upload_to='images/reference_image/', verbose_name='图片3'),
        ),
        migrations.AlterField(
            model_name='incominginspectiondetail',
            name='image4',
            field=models.ImageField(blank=True, null=True, upload_to='images/reference_image/', verbose_name='图片4'),
        ),
    ]
