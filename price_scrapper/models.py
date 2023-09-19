from django.db import models

class Product(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    target_link = models.URLField(max_length=255, null=True, blank=True)
    crawl_status = models.CharField(max_length=50, default="No Price")