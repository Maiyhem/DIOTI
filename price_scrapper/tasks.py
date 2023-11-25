# myapp/tasks.py

from datetime import timezone
import datetime
from celery import shared_task
from django.http import JsonResponse
import requests
from .views import woocomerce_login, check_price_change ,get_exchange_rate,scrape_price,update_website_price
import random
from .models import Product


def web_update_all_prices():
    products = Product.objects.all()
    for product in products:
        product_id = product.id
        product_name= product.name
        status = product.crawl_status
        target_link = product.target_link
        if 'Success' in  status :
            update_website_price(product)
        else :
            print(f'error : {product_id}: {product_name}')
        # Add your price scraping code here
    return True




def scrap_update_all_prices():
    products = Product.objects.all()
    exchange_rate = get_exchange_rate()
    for product in products:
        if product.target_link:
           linkprice = scrape_price(product.target_link)
           if linkprice:
                if (linkprice != 'CallUs') and ('error' not in linkprice):
                    product.scrap_price = linkprice
                    product.crawl_status = "Success"
                    product.last_scrape = timezone.now()
                    product.save()
                    print(f'Updated Database price for {product.name} to {linkprice}')
                elif product.AED_price and exchange_rate != None:
                    product.scrap_price = product.AED_price * exchange_rate
                    product.crawl_status = "No link Success AED"
                    product.last_scrape = timezone.now()
                    product.save()
                else :
                    product.scrap_price = ''
                    product.crawl_status = "Error or Callus"
                    product.last_scrape = timezone.now()
                    product.save()
        elif product.AED_price and exchange_rate != None:
            product.scrap_price = product.AED_price * exchange_rate
            product.crawl_status = "Success AED"
            product.last_scrape = timezone.now()
            product.save()

    response_data = {'message': 'Success'}
    return JsonResponse(response_data)



def sync_product_list():
    base_url = 'https://doorbinshot.com/wp-json/wc/v3'
    endpoint = '/products'
    page = 1
    per_page = 100
    auth_header = woocomerce_login()

    while True:
        url = f'{base_url}{endpoint}?per_page={per_page}&page={page}'
        
        payload = {}
        try:
            response = requests.get(url, headers=auth_header)
            
            if response.status_code == 200:
                products_data = response.json()
                #print(response.content)
                if not products_data:
                    break  #No more products to retrieve

                for product in products_data:
                    try:
                        # Try to get the existing product with the given id
                        existing_product = Product.objects.get(id=int(product['id']))
                    except Product.DoesNotExist:
                        # If it doesn't exist, create a new product
                        existing_product = None
                    if existing_product is None: 
                        p =  Product.objects.get_or_create(id = int(product['id']),name = product['name'], web_price = product['regular_price'])
                        if p :
                            print(f"Created product with ID {product['id']}")
                    else:
                        # Product already exists, you can choose to do something with it if needed
                        if existing_product.target_link == '' and existing_product.AED_price == '':
                            existing_product.web_price =  product['regular_price']
                        #print(f"Product with ID {product['id']} already exists.")
                        pass

                page += 1  #Move to the next page of results
            else:
                print(f'Error: {response.text}')
                print(str(response.content).encode('utf-8'))
                break  # Exit the loop on error
        except:
            pass


    return JsonResponse({'message': 'Success'})
@shared_task
def periodic_task():
    #1st sync product_list
    sync_product_list()

    print('UPDATE PRODUCT LIST SUCCESS')
    if check_price_change() : 
            print('PRICES HAS CHANGED.scrapping all')
            #scrape prices

            scrap_update_all_prices()
            
            print('START WEB UPDATE')
            
            web_update_all_prices()
            #update website price
    else:
        pass
    return 'SUCCESSFULLY FINISHED'