# Generated by Django 4.2.5 on 2023-09-19 14:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('price_scrapper', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='price',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
