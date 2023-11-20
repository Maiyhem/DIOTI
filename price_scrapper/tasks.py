# myapp/tasks.py

from celery import shared_task
from .views import check_price_change
import random
from .models import Product

@shared_task
def periodic_task():
    products = random.sample(list(Product.objects.filter(crawl_status='Success')), 10)
    for product in products:
        check_price_change(product)
