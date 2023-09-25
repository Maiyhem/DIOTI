# Generated by Django 4.2.5 on 2023-09-19 14:07

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('price', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('target_link', models.URLField(blank=True, max_length=255, null=True)),
                ('crawl_status', models.CharField(default='No Price', max_length=50)),
            ],
        ),
    ]
