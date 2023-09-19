from django.shortcuts import render

from django.http import HttpResponse
from .models import Product
# Create your views here.

def product_list(request):
    products = Product.objects.all()
    return render(request, 'product_list.html', {'products': products})

def scrape_prices(request):
    # Add your price scraping code here
    return HttpResponse("Prices scraped and updated successfully.")

def update_prices(request):
    # Add your price updating code here
    return HttpResponse("Prices updated successfully.")