from django.db import models

class Product(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    price = models.CharField(max_length =  20 ,null=True, blank=True)
    target_link = models.URLField(max_length=255, null=True, blank=True)
    crawl_status = models.CharField(max_length=50, default="No Price")
    

    def  __str__(self) -> str:
        return str(self.id)+self.name