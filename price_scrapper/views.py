from bs4 import BeautifulSoup
from django.shortcuts import render
import sqlite3
import base64
import requests
from django.http import HttpResponse
from .models import Product
import json

# Create your views here.

def index(request):

    return render(request, 'product_list.html',)


def product_list(request):
    products = Product.objects.all()
    return render(request, 'table.html', {'products': products})


# Define a function to scrape the price from a given URL and save HTML to a file
def scrape_price(url, product_name):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            price = None
            # Check the website domain and extract the price accordingly
            if "https://www.afrangdigital.com/" in url:
                price_element = soup.find('span', itemprop='price')
                if price_element:
                    price = price_element.get_text(strip=True)
                    if price != 'تماس بگیرید':
                        price = price.replace('ریال', '').replace(',', '').strip()
                        price = price[0:len(price)-1]
                    else:
                        price = 'CallUs'
            elif "https://noornegar.com/" in url:
                product_box = soup.find('div', class_ = 'products-inner')
                soup = product_box
                price_element = soup.find('span', class_='woocommerce-Price-amount')
                if price_element:
                    price = price_element.find('bdi').get_text(strip=True)
                    if price:
                        price = price.replace('تومان', '').replace(',', '').strip()
                        price = translate_persian_numerals_to_latin(price)
                else:
                    price = 'CallUs'
            elif "https://www.didnegar.com/" in url:
                product_box = soup.find('div', class_ = 'product-box')
                soup = product_box
                price_element = soup.find('span', class_='woocommerce-Price-amount')
                if price_element:
                    price = price_element.get_text(strip=True)
                    if price:
                        price = price.replace('تومان', '').replace(',', '').strip()
                        price = translate_persian_numerals_to_latin(price)
                else:
                    price = 'CallUs'
            return price
    except Exception as e:
        print(f"Error scraping price from {url}: {e}")
    return None





def scrap_update_all_prices(request):
    products = Product.objects.all().exclude(target_link = None)
    for product in products:
        product_id = product.id
        product_name= product.name
        target_link = product.target_link
        if target_link:
            price = scrape_price(target_link, product_name)
            if price:
                if price != 'CallUs':
                    product.price = price
                    product.crawl_status = "Success"
                    product.save()
                    update_website_price(product)
                    print(f'Updated price for {product_name} to {price}')
                else:
                    product.price = price
                    product.crawl_status = "Call Us Price"
                    product.save()
                    update_website_price(product)
                    print(f'Callus price for {product_name} ')
            else:
                product.price = "No Price"
                product.crawl_status = "Could not scrape price"
                product.save()
                update_website_price(product)
                print(f'Failed to update price for {product_name}')
        # Add your price scraping code here
        return HttpResponse("Prices scraped and updated successfully.")




def translate_persian_numerals_to_latin(text):
    persian_numerals = '۰۱۲۳۴۵۶۷۸۹'
    latin_numerals = '0123456789'
    translation_table = str.maketrans(persian_numerals, latin_numerals)
    return text.translate(translation_table)


def update_website_price(product):
    product_id = product.id
    new_price = product.price
    status = product.crawl_status
    link = product.target_link
    product_name = product.name
    base_url = 'https://doorbinshot.com/wp-json/wc/v3'
    endpoint = '/products'
    update_url = f'{base_url}{endpoint}/{product_id}'
    headers = woocomerce_login()
    new_price_data = {
            'regular_price': new_price
        }
    print(new_price)

    
    if link != '':
    
        # Construct the update URL for the specific product
        # Define the new price in the format expected by WooCommerce
        # Send a PUT request to update the product price
        response = requests.put(update_url, headers=headers, data = json.dumps(new_price_data))

        if response.status_code == 200:
            print(response.content.decode('utf-8'))
            print(f'Successfully updated price for Product ID {product_id}{product_name}')
        else:
            print(response.content.decode('utf-8'))
            print(f'Error updating price for Product ID {product_id}: {response.status_code}')
    return

def update_product_list(request):
    
    base_url = 'https://doorbinshot.com/wp-json/wc/v3'
    endpoint = '/products'
    page = 1  # Start with the first page of results
    per_page = 100  # Adjust per_page as needed to retrieve a larger number of products per page
    auth_header = woocomerce_login()
    while True:
        url = f'{base_url}{endpoint}?per_page={per_page}&page={page}'
        
        payload = {}
        
        response = requests.get(url, headers=auth_header)
        
        if response.status_code == 200:
            products_data = response.json()
            #print(response.content)
            if not products_data:
                break  #No more products to retrieve
            
            for product in products_data:

                print (int(product['id']),"---",product['name'],"---",product['regular_price'])
                p =  Product.objects.get_or_create(id = int(product['id']),name = product['name'], price = product['regular_price'])


            page += 1  #Move to the next page of results
        else:
            print(f'Error: {response.status_code}')
            print(str(response.content).encode('utf-8'))
            break  # Exit the loop on error

    #print("Products data successfully stored in the database.")
    return True


def woocomerce_login():

    api_key = 'ck_1a5bdfc26bafef0e54b8855484f48e8d4652d3fc'  # Replace with your actual API key
    api_secret = 'cs_46f0378584d13e45fc1ce25a90a9b78fa70e2666'  # Replace with your actual API secret
    auth_string = f'{api_key}:{api_secret}'
    auth_header = 'Basic ' + base64.b64encode(auth_string.encode()).decode()
    headers = {
        'Authorization': auth_header    }

    return headers