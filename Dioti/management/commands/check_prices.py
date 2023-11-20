import random
from django.core.management.base import BaseCommand
from price_scrapper.views import check_price_change
from price_scrapper.models import Product

class Command(BaseCommand):
    help = 'Check prices for randomly selected products'

    def handle(self, *args, **options):
        products = random.sample(list(Product.objects.filter(crawl_status='Success')), 10)
        for product in products:
            check_price_change(product)
        self.stdout.write(self.style.SUCCESS('Successfully checked prices for 10 products.'))