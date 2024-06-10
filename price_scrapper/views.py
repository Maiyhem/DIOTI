
import random
import time
from django.utils import timezone
from bs4 import BeautifulSoup
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST
import sqlite3
import base64
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from .models import Product
import json
import logging
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.utils import timezone
import datetime
# Create your views here.


logger = logging.getLogger('myapp')
logger.setLevel(logging.INFO)
def index(request):
    '''product_id_list = [31561,30686,30642,30597,30557,30533,30508,30453,30436,30398,30365,30342,30300,30281,29533,29481,29472,27949,27259,27223,27060,26200,26196,26167,26144,26127,26115,26091,25596,21602,21527,20454,20339,19466,19353,18919,18360,17934,17197,17165,16937,16064,16041,15632,15537,15530,15514,15121,15089,14874,14063,13756,13644,12110,11804,11671,11666,11657,11649,11646,11644,11641,11546,11516,11506,11487,11433,11413,11190,11111,11083,11078,11072,11069,11066,11063,11054,11050,11048,10988,10822,10795,10395,10380,10375,10310,10266,10248,10208,10130,10073,9993,9698,9113,9108,9102,9090,9089,9084,9079,9032,9030,8985,8974,8968,8959,8947,8938,8917,8901,8876,8856,8847,8835,8692,8674,8660,8647,8635,8624,8606,8595,8584,8573,8565,8550,8548,8543,8538,8532,8526,8519,8514,8509,8503,8493,8484,8478,8472,8467,8462,8372,8171,8166,8160,8159,8094,8068,8039,8007,7996,7980,7965,7954,7948,7935,7913,7901,7883,7858,7813,7789,7661,7647,7633,7616,7584,7575,7538,7508,7501,7490,7466,7424,7413,7341,7324]
    for product_id in product_id_list :
        add_comment_to_product(product_id)'''
    logger.debug('This is a debug message')
    logger.info('This is an info message')
    logger.warning('This is a warning message')
    logger.error('This is an error message')
    logger.critical('This is a critical message')
    '''for p in Product.objects.all():
            p.last_scrape = timezone.now()-datetime.timedelta(hours=6) 
            p.save()
            print(p.id)'''
    return render(request, 'Mpage.html',)


@login_required(login_url="/accounts/login/")
def products(request):
    products = Product.objects.all()
    
    return render(request, 'products.html', {'products': products})


@login_required(login_url="/accounts/login/")
def logs(request):
    products = Product.objects.all()
    return render(request, 'logs.html', {'products': products})


@login_required(login_url="/accounts/login/")
def dashboard(request):

    success_num = Product.objects.filter(crawl_status = 'Success').count()
    error_num = Product.objects.exclude(crawl_status__in = ['Success' , 'Call Us Price']).count()
    callus_num = Product.objects.filter(crawl_status = 'Call Us Price').count()
    context ={
        'success_num': success_num,
        'error_num': error_num,
        'callus_num': callus_num,
    }
    return render(request, 'dashboard.html',context)




@login_required(login_url="/accounts/login/")
def product_list(request):
    products = Product.objects.all()
    return render(request, 'table.html', {'products': products})



@require_POST
def update_product(request):
    product_id = request.POST.get('product_id')
    product = get_object_or_404(Product, id=product_id)

    # Update the product fields with the form data
    product.name = request.POST.get('name')
    product.web_price = request.POST.get('web_price')
    product.AED_price = request.POST.get('AED_price')
    product.scrap_price = request.POST.get('scrap_price')
    product.target_link = request.POST.get('target_link')
    product.crawl_status = request.POST.get('crawl_status')
    product.last_scrape = request.POST.get('last_scrape')
    product.last_web_price_update = request.POST.get('last_web_price_update')

    # Save the updated product
    product.save()

    return JsonResponse({'success': True})

# Define a function to scrape the price from a given URL and save HTML to a file

def scrape_done(request):

    products = Product.objects.exclude(crawl_status = 'Success')

    
    return render(request, 'no_price.html', {'products': products})


def scrape_price(url):
    try:
        #logger.info(f'getting url {url}')
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            price = None
            if "https://www.afrangdigital.com/" in url:
                price_element = soup.find('span', itemprop='price')
                if price_element:
                    price = price_element.get_text(strip=True)
                    if price != 'تماس بگیرید':
                        price = price.replace('ریال', '').replace(',', '').strip()[:-1]
                    else:
                        price = 'CallUs'
            elif "https://noornegar.com/" in url or "https://www.didnegar.com/" in url:
                product_box = soup.find('div', class_='products-inner') if "https://noornegar.com/" in url else soup.find('div', class_='woocommerce-main-3-row-single')
                price_element = product_box.find('span', class_='woocommerce-Price-amount') if product_box else None
                if price_element:
                    price = price_element.find('bdi').get_text(strip=True)
                    if price:
                        price = translate_persian_numerals_to_latin(price.replace('تومان', '').replace(',', '').strip())
                else:
                    price = 'CallUs'
            return price
    except Exception as e:
        return f'error {e}'


@login_required(login_url="/accounts/login/")
def scrap_update_all_prices(request):
    #one_hour_ago = timezone.now() - datetime.timedelta(hours=1)
    products = Product.objects.exclude(target_link= None)
    #exchange_rate = get_exchange_rate()
    logger.info(products.count())
    logger.info('###########Scrap Start###########')
    
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {executor.submit(scrape_price, product.target_link): product for product in products 
                   if (product.last_scrape and (product.last_scrape < timezone.now() - datetime.timedelta(hours=1)) or not product.last_scrape) }
        for future in as_completed(futures):
            product = futures[future]
            #print(product.last_scrape < timezone.now() - datetime.timedelta(hours=1) )
            try:
                price = future.result()
                if price and 'error' not in price:
                    if price != 'CallUs':
                        product.scrap_price = price
                        product.crawl_status = "Success"
                    else:
                        product.crawl_status = "Call Us Price"
                    product.last_scrape = timezone.now()
                    product.save()
                    logger.info(f'Updated Database price for {product.name} to {price}')
                else:
                    product.scrap_price = ""
                    product.crawl_status = price
                    product.last_scrape = timezone.now()
                    product.save()
                    logger.info(f'Failed to update price for {product.name}')
            except Exception as e:
                logger.error(f"An error occurred: {e}")


    logger.info('###########Scrap Ended###########')
    return JsonResponse({'message': 'Success'})




@login_required(login_url="/accounts/login/")
def web_update_all_prices(request):
    products = Product.objects.filter(
        target_link__isnull=False,
        crawl_status__in=['Success', 'Call Us Price']
    ).exclude(target_link__in =['None',None])
    logger.info('###########WebUpdate Start###########')
     
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(update_website_price, product): product for product in products 
                   if (product.last_web_price_update and (product.last_web_price_update < timezone.now() - datetime.timedelta(hours=1))) or not product.last_web_price_update}
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                product = futures[future]
                logger.error(f"An error occurred with product {product.id}: {e}")

    logger.info('###########WebUpdate End###########')
    logger.handlers[0].flush()  # 
    return JsonResponse({'success' :True})

def update_website_price(product):
    if not product.target_link:
        logger.info(f'No target_link for product id: {product.id}: {product.name}')
        return

    product_id = product.id
    new_price = product.scrap_price
    status = product.crawl_status
    link = product.target_link
    product_name = product.name
    base_url = 'https://doorbinshot.com/wp-json/wc/v3'
    endpoint = '/products'
    update_url = f'{base_url}{endpoint}/{product_id}'
    headers = woocomerce_login()

    new_price_data = {
        'regular_price': '' if new_price == 'CallUs' else new_price
    }

    if product.last_web_price_update is None or product.last_web_price_update < (timezone.now() - datetime.timedelta(days=1)):
        response = requests.put(update_url, headers=headers, data=json.dumps(new_price_data))
        if response.status_code == 200:
            product.last_web_price_update = timezone.now()
            product.save(update_fields=['last_web_price_update'])
            logger.info(f'Web Price updated Product ID {product_id} : {product_name} : {new_price}')
        else:
            logger.info(response.content.decode('utf-8'))
            logger.info(f'Error updating price for Product ID {product_id} : {response.status_code}')
    return
@login_required(login_url="/accounts/login/")
def update_product_targetlink(request):
    if request.method == "POST":
        # Get the product ID and updated target link from the POST data
        product_id = request.POST.get("product_id")
        updated_target_link = request.POST.get("target_link")

        # Perform the update here (e.g., update the Product model)
        try:
            product = Product.objects.get(pk=product_id)
            product.target_link = updated_target_link
            product.save()
            return JsonResponse({"success": True})
        except Product.DoesNotExist:
            pass

    return JsonResponse({"success": False})


def translate_persian_numerals_to_latin(text):
    persian_numerals = '۰۱۲۳۴۵۶۷۸۹'
    latin_numerals = '0123456789'
    translation_table = str.maketrans(persian_numerals, latin_numerals)
    return text.translate(translation_table)


@login_required(login_url="/accounts/login/")
def update_product_list(request):
    base_url = 'https://doorbinshot.com/wp-json/wc/v3'
    endpoint = '/products'
    page = 1
    per_page = 100
    auth_header = woocomerce_login()

    # To keep track of product IDs retrieved from WooCommerce
    woocommerce_product_ids = set()
    retry_attempts = 5

    while True:
        url = f'{base_url}{endpoint}?per_page={per_page}&page={page}'
        for attempt in range(retry_attempts):
            try:
                response = requests.get(url, headers=auth_header)
                if response.status_code == 200:
                    products_data = response.json()
                    if not products_data:
                        break  # No more products to retrieve

                    for product in products_data:
                        product_id = int(product['id'])
                        woocommerce_product_ids.add(product_id)

                        try:
                            # Try to get the existing product with the given id
                            existing_product = Product.objects.get(id=product_id)
                        except Product.DoesNotExist:
                            # If it doesn't exist, create a new product
                            existing_product = Product(id=product_id)

                        existing_product.name = product['name']
                        existing_product.web_price = product.get('regular_price', '')
                        existing_product.save()
                        logger.info(f'Synchronized product with ID {product_id}')

                    page += 1  # Move to the next page of results
                    break  # Exit the retry loop on success
                else:
                    logger.error(f'Error: {response.text}')
                    break  # Exit the loop on error
            except (requests.exceptions.ConnectionError, ConnectionResetError) as e:
                logger.error(f'Exception occurred: {e}')
                if attempt < retry_attempts - 1:
                    logger.info(f'Retrying... ({attempt + 1}/{retry_attempts})')
                    time.sleep(5)  # Wait for 5 seconds before retrying
                else:
                    logger.error('Max retries reached, exiting.')
                    return JsonResponse({'message': 'Failed to sync products due to connection issues.'})

    # Delete products in the Django database that were not retrieved from WooCommerce
    Product.objects.exclude(id__in=woocommerce_product_ids).delete()

    logger.info("Products data successfully synchronized with WooCommerce.")
    return JsonResponse({'message': 'Success'})





@login_required(login_url="/accounts/login/")
def woocomerce_login(request):

    api_key = 'ck_a862f3205a9991d1bed42d48104616f92fa702e7'  # Replace with your actual API key
    api_secret = 'cs_fe83d949d4d90a1f2fba42b903ab87b256543f06'  # Replace with your actual API secret
    auth_string = f'{api_key}:{api_secret}'
    auth_header = 'Basic ' + base64.b64encode(auth_string.encode()).decode()
    headers = {
        'Authorization': auth_header ,
        'Content-Type': 'application/json'
        }

    return headers




@login_required(login_url="/accounts/login/")
def check_price_change():
    products = random.sample(list(Product.objects.filter(crawl_status='Success')), 20)
    total_change_status= []
    
    for product in products:
        try:
            url = product.target_link
            response = requests.get(url)
            price = None
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
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
                    product_box = soup.find('div', class_ = 'woocommerce-main-3-row-single')
                    soup = product_box
                    price_element = soup.find('span', class_='woocommerce-Price-amount')
                    
                    if price_element:
                        price_element.find('bdi',class_='true_price')
                        price = price_element.get_text(strip=True)
                        if price:
                            price = price.replace('تومان', '').replace(',', '').strip()
                            price = translate_persian_numerals_to_latin(price)
                    else:
                        price = 'CallUs'
        
            if price and price != product.scrap_price :
                total_change_status.append('changed')
                logger.info('changed')

            logger.info(str(product.id) + 'not changed')
        except Exception as e:
            logger.info(f'Error checking price for Product ID {product.id}: {str(e)}')
            pass
    if len(total_change_status) > 3:
        return True
    else:
        return False


@login_required(login_url="/accounts/login/")
def get_exchange_rate():
    url = "https://www.tgju.org/profile/price_aed"
    response = requests.get(url)
    if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            target_element = soup.select_one("#main > div.stocks-profile > div.fs-row.bootstrap-fix.widgets.full-w-set.profile-social-share-box > div.row.tgju-widgets-row > div.tgju-widgets-block.col-md-12.col-lg-4.tgju-widgets-block-bottom-unset.overview-first-block > div > div:nth-child(2) > div > div.tables-default.normal > table > tbody > tr:nth-child(1) > td.text-left")
            aed_price =  target_element.get_text()
            aed_price = aed_price.replace(',', '').strip()
            #logger.info(aed_price)
            return aed_price
    else :
        logger.info('error geting exchange rate')
        return None

    ''' try:
        # توکن دسترسی خود را جایگزین YOUR_ACCESS_KEY کنید.
        access_key = '2ae1cde49f8dc5311957fe25'
        
        # اینجا شما می‌توانید پارامترهای خود را برای درخواست تعیین کنید.
        params = {
            'access_key': access_key,
            'base': 'GBP',  # ارز پایه
            'symbols': 'AED,IRR'  # نمادهای ارزی که می‌خواهید نرخ مبادله آنها را دریافت کنید.
        }
        
        api_url = 'https://v6.exchangerate-api.com/v6/'+access_key+'/history/AED/2023/11/24'
        response = requests.get(api_url,)
        logger.info(response.json())
        api_url = 'https://v6.exchangerate-api.com/v6/'+access_key+'/latest/IRR'
        response = requests.get(api_url,)

        if response.status_code == 200:
            data = response.json()
            logger.info(data)
            # اینجا می‌توانید از داده‌های دریافتی برای محاسبه نرخ مبادله استفاده کنید.
            # بر اساس داده‌های دریافتی، exchange_rate را تعیین کنید.
            exchange_rate = data['rates']['AED']
            
            return exchange_rate
        else:
            data = response.json()
            logger.info(data)
            return None
    except Exception as e:
        logger.info(f"Error getting exchange rate: {e}")'''
    return None


# Function to generate a random date within the last 4 months
def random_date():
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=120)  # 4 months ago
    random_datetime = start_date + datetime.timedelta(days=random.randint(0, 120))
    return random_datetime.strftime('%Y-%m-%dT%H:%M:%S')

# Function to generate a random rating between 3 and 5
def random_rating():
    return round(random.uniform(4, 5))


# Function to add a comment to a product

@login_required(login_url="/accounts/login/")
def add_comment_to_product(product_id):
    url = 'https://doorbinshot.com/wp-json/wc/v3'
    endpoint = f"{url}/products/reviews"
    names = [

    "user1234", "alpha_98", "dreamer22", "cool_cat", "sunshine23", "silver_star", "wanderlust_89", "neon_ninja",
    "mystic_unicorn", "galaxy_gazer", "midnight_wolf", "enchanted_rose", "rainbow_dreamer", "cosmic_butterfly",
    "secret_sorcerer", "melody_maker", "starlight_dancer", "aurora_borealis", "twilight_sparkle", "phantom_phoenix",
    "user5678", "beta_99", "visionary33", "hot_dog", "moonlight42", "golden_globe", "adventurer_92", "electric_eel",
    "enchanted_forest", "starry_night", "sapphire_dragon", "whispering_wind", "lunar_lover", "stellar_dreamer",
    "ocean_waves", "crimson_crown", "dream_weaver", "sunset_bliss", "magic_mermaid", "emerald_enigma", "silver_shadow",
    "user2468", "gamma_100", "wanderer44", "frosty_flame", "sunflower66", "diamond_dust", "mystical_moon", "echo_echo",
    "wonderland_wanderer", "jupiter_jumper", "celestial_siren", "nebula_navigator", "velvet_voyager", "rose_petals",
    "twinkle_toes", "whispering_willow", "evergreen_echo", "crystal_clear", "shadow_shifter", "user1357", "delta_101",
    "zen_master", "flying_fish", "nightingale88", "cosmic_chemist", "galactic_guru", "enchanted_elf", "moonlit_magic",
    "dream_catcher", "solar_sorceress", "stardust_seeker", "echoing_essence", "serenity_spirit", "wild_wonder",
    "starlit_sailor", "crimson_cloud", "fairy_frost", "whispering_whale", "velvet_vortex", "user9876", "epsilon_102",
    "dreamer's_delight", "flaming_phoenix", "sunrise_spectacle", "mystic_meadow", "luminous_lotus", "shooting_star",
    "wandering_wisp", "serendipity_seeker", "silken_shadow", "emerald_echo", "sapphire_song", "user3698", "zeta_103",
    "lost_in_lavender", "crimson_kiss", "dazzling_dragonfly", "lunar_light", "whispering_woods", "eternal_embrace",
    "frostbite_flower", "moonshadow_melody", "starshine_soul", "twilight_trail", "whirlwind_whisper", "user7410",
    "theta_104", "wandering_warrior", "floral_fantasy", "solar_specter", "galactic_garden", "enchanted_eternity",
    "midnight_mystery", "dreamy_dragon", "whispering_willow", "shooting_starlet", "luminous_lagoon", "user1593",
    "iota_105", "stargazer's_sanctuary", "mystic_mountain", "twilight_tale", "serene_sapphire", "whispering_wonderer",
    "frosty_firefly", "celestial_cascade", "sunset_serenade", "dancing_dreamer", "user3021", "kappa_106", "moonlit_mirage",
    "whispering_winds", "galactic_glory", "starlight_synergy", "mystical_mist", "emerald_enchantment", "lunar_lullaby",
    "cosmic_cadence", "azure_angel", "crimson_cascade", "dreamy_dawn", "user5184", "lambda_107", "luminous_leap",
    "serene_soul", "whispering_wonders", "galactic_gleam", "lunar_love", "celestial_chronicle", "twilight_tide",
    "starry_song", "dreamscape_delight", "user9473", "mu_108", "moonlit_marvel", "whispering_wishes", "solar_serenity",
    "galactic_grace", "luminous_lagoon", "celestial_celebration", "twilight_tune", "starry_skies", "user1230", "nu_109",
    "whispering_wonderland", "stellar_serenade", "cosmic_conquest", "lunar_luster", "emerald_echoes", "celestial_crescendo",
    "twilight_twist", "shimmering_shores", "user4567", "xi_110", "moonlit_melody", "whispering_wanderlust", "solar_symphony",
    "galactic_glow", "luminous_legend", "celestial_carnival", "twilight_tango", "starry_saga",
    "آرمین مهدوی",
    "مهراد رضایی",
    "ابراهیمی",
    "آتنا رحیمی",
    "سپهر جعفری",
    "نازنین قاسمی",
    "امیرحسین میرزایی",
    "الهام",
    "شایان محمدی",
    "محمدرضا علیزاده",
    " حسینی",
    "پارسا احمدی",
    "سارینا علیمحمدی",
    "بحقیقی",
    "امیر علی نژاد",
    "سحر نظری",
    "رضا رحمانی",
    "مهسا ",
    "سارا کریمی",
    "امیرمهدی فرجی",
    "پریسا قاسمیان",
    "علی رضا زارعی",
    "ساناز محمدزاده",
    "محمد ",
    "ناصر صالحی",
    "مهرزاد عبداللهی",
    "مهتا محمدیان",
    "سجاد موسوی",
    "آرمان رحمانی",
    "پریناز محمدی",
    "شهاب احمدی",
    "نیما صفری",
    "نگار جعفری",
    "میترا قاسمی",
    "فرزاد کریمی",
    "فاطمه زهرا حسینی",
    "مهدی خانزاده",
    "پرستو محمدی",
    "آرش جعفری",
    "نگار محمدی",
    "رضا موسوی",
    "مهرداد اکبری",
    "نرگس رحیمی",
    "بهروز نوروزی",
    "المیرا قاسمی",
    "شایان رضایی",
    "سارینا رحمانی",
    "سپهر ",
    "نیما صادقی",
    "ماندانا محمدی",
    "امیرمهدی ",
    "رضا زارعی",
    "ساناز اکبری",
    "آتوسا ",
    "محمدرضا کرمی",
    "آتنا صادقی",
    "سیمین ",
    "شهریار حسینی",
    "آرمین رحمانی",
    "امیرحسین ",
    "آتوسا حسینی",
    "شهرام محمدی",
    "میلاد ",
    "پارسا محمدی",
    "آرش حقیقی",
    "پریسا ",
    "نیما علیزاده",
    "فریدون ",
    "نگین رحیمی",
    "پارسا ",
    "سارینا ",
    "زارعیان",
    "شهریار علیزاده",
    "موسوی",
    "فاطمه زهرا عبداللهی",
    "مهرداد صالحی",
    "ساناز قاسمی",
    "نازنین رحیمی",
    "آتنا محمدی",
    "آرمان عبداللهی",
    "پرستو ",
    "رضا ",
    "شهاب ",
    "پریناز رضایی",
    "فرزاد ",
    "سارا محمدی",
    "پریسا رحمانی",
    "نازنین صفری",
    "مهسا ",
    "نازنین موسوی",
    "آرمین ",
    "سجاد رحمانی",
    "ساناز رضایی",
    "آتنا صادقی",
    "فاطمه زهرا محمدی",
    "نازنین رضایی",
    "نرگس علیمحمدی",
    "پرستو حسینی",
    "آرمین حقیقی",
    "ساناز حسینی",
    "آرمان ابراهیمی",
    "سهیلا محمدی",
    "آتنا محمدیان",
    "فریدون احمدی",
    "Armin Mahdavi",
    "Mehrad Rezai",
    "Negin Ebrahimi",
    "Atena Rahimi",
    "Sepehr Jafari",
    "Nazanin Ghasemi",
    "Amirhossein Mirzaii",
    "Elham Sadeghi",
    "Shayan Mohammadi",
    "Mohammadreza Alizadeh",
    "Elnaz Hosseini",
    "Parsa Ahmadi",
    "Sarina Alimohammadi",
    "Behnaz Haghighi",
    "Amir Ali Nezhad",
    "Sahar Nazari",
    "Reza Rahmani",
    "Mahsa Mousavi",
    "Sara Karimi",
    "Sarina Rahmani",
    "Sepehr Rahmani",
    "Nima Sadeghi",
    "Mandana ",
    "Amirmehdi Farahani",
    "Reza Zarei",
    "Sanaz Akbari",
    "Atousa ",
    "Mohammadreza Karimi",
    "Atena Sadeghi",
    "Simin Zarei",
    "Shahriar Hosseini",
    "Armin Rahmani",
    "Amirhossein ",
    "Atousa Hosseini",
    "Shahram Mohammadi",
    "Milad Rezaii",
    "Parsa Mohammadi",
    "Arash Haghighi",
    "Parisa Karimi",
    "Nima Alizadeh",
    "Fereidon ",
    "Negin Rahimi",
    "Parsa Akbari",
    "Sarina ",
    "Reza Zareian",
    "Shahriar ",
    "Parnaz Rezai",
    "Farzad ",
    "Sara Mohammadi",
    "Parisa Rahmani",
    "Nazanin Safari",
    "Sonya Maghami",
    "Manesh ",
    "Mina Saedi",
    "Navid Hosseini",
    "Arman Rahmani",
    "Seyed ",
    "Vahid ",
    "Mahin Shahidi",
    "Yasmin Khalili",
    "Fereshteh Abbasi",
    "Mohammad Ebrahimzadeh",
    "Maryam Hoseini",
    "Shirin Jamshidi",
    "Neda Eskandari",
    "Amir Ali Ahmadi",
    "Pouya Moradi",
    "Nima Hatami",
    "Arman Ahmadi",
    "Mohammad Esmaili",
    "Farhad Mohammadi",
    "Armin ",
    "Nima Azimi",
    "Neda Rostami",
    "Ali Rezaei",
    "Reza ",
    "Ali Mohammadi",
    "Mehdi Gholami",
    "Arash Jamali",
    "Sina ",
    "Parsa Razavi",
    "Ava Khosravi",
    "Kiana ",
    "Darya Khalaj",
    "Reza Shafiei",
    "Mohammad Rostami",
    "Mahsa Bahrami",
    "Amir Sohrabi",
    "Reza ",
    "Sara Kazemi",
    "Maryam Salehi",
    "Saman Dehghan",
    "Mehran ",
    "Mehdi Safari",
    "Mahdi Asadi",
    "Mohsen Najafi",
    "Fatemeh Tavakoli",
    "Arash ",
    "Hamed Rezaei",
    "Shirin Naderi",
    "Mohammad Ali Asgari",
    "Bahram ",
    "Zahra Zare",
    "Reza Hashemi",
    "Arman Ebrahimi",
    ]
    comments = [
    "سلام، اینجا واقعا بهترین فروشگاه آنلاینه!",
    "من کاملا از خریدم راضی هستم. ارسال سریع و کیفیت بالا!",
    "با این فروشگاه تجربه خرید بسیاری داشتم و همیشه راضی بودم.",
    "محصولاتشون واقعا خوبه، همیشه از اینجا خرید می‌کنم.",
    "از این فروشگاه خیلی راضیم. همیشه محصولات با کیفیت و به موقع می‌فرستند.",
    "هیچ وقت از این فروشگاه ناراضی نشدم. کاملا توصیه می‌شه!",
    "خریدم از این فروشگاه را به همه پیشنهاد می‌کنم. عالیه!",
    "محصولاتشون واقعاً عالیه، من کاملاً از خریدم راضیم.",
    "با این فروشگاه تجربه خوبی داشتم. کیفیت و قیمت مناسبی دارند.",
    "از این فروشگاه واقعاً راضیم. هیچ وقت مشکلی نداشتم.",
    "من از این فروشگاه خیلی خوشم می‌آد. همیشه به موقع و با کیفیت ارسال می‌کنند.",
    "از تجربه خریدم از این فروشگاه بسیار خوشم آمده. ممنون از شما!",
    "فروشگاه فوق‌العاده‌ایه. هیچگاه ناامید نشده‌ام.",
    "از این فروشگاه واقعا راضی هستم. محصولات با کیفیت و قیمت مناسبی دارند.",
    "محصولاتشون واقعا با کیفیته. هیچ وقت مشکلی نداشتم.",
    "از تجربه خریدم از این فروشگاه بسیار خوشم آمده. حتما به دیگران هم پیشنهاد می‌کنم.",
    "من همیشه از این فروشگاه خرید می‌کنم. هیچ وقت ناامید نشده‌ام.",
    "فروشگاه عالییییه! همیشه کیفیت و قیمت مناسبی دارند.",
    "از این فروشگاه بسیار راضی هستم. تنوع محصولات و خدمات عالی دارند.",
    "من از این فروشگاه خیلی خوشم می‌آد. هیچ وقت مشکلی نداشته‌ام.",
    "تجربه‌ی خوبی داشتم با این فروشگاه. حتما به دوستانم هم پیشنهادش می‌کنم.",
    "از تجربه خریدم از این فروشگاه بسیار راضی هستم. همیشه به موقع و با کیفیت ارسال می‌کنند.",
    "از فروشگاه شما خیلی راضیم. محصولات با کیفیتی دارید.",
    "محصولات فوق‌العاده‌ای دارید. همیشه از شما خرید می‌کنم.",
    "تنوع محصولات واقعا زیاده. هر چیزی که نیاز داشتم اینجا پیدا کردم.",
    "خدمات شما عالیه. همیشه با ارزش‌ترین محصولات را ارائه می‌دهید.",
    "از تجربه خریدم از این فروشگاه بسیار راضی هستم. همیشه محصولات با کیفیتی را دریافت می‌کنم.",
    "فروشگاه شما واقعاً عالیه. همیشه سریع و با کیفیت ارسال می‌کنید.",
    "من از این فروشگاه بسیار راضیم. همیشه محصولات با کیفیتی را دریافت می‌کنم.",
    "از تجربه خریدم از این فروشگاه بسیار راضی هستم. محصولات بسیار با کیفیتی دارید.",
    "فروشگاه شما همیشه عالی عمل می‌کند. هیچ وقت ناامید نشده‌ام.",
    "از تجربه خریدم از این فروشگاه بسیار راضی هستم. خدمات شما بسیار حرفه‌ای است.",
    "محصولات شما همیشه با کیفیت و قیمت مناسبی هستند. همیشه از شما خرید می‌کنم.",
    "فروشگاه شما همیشه خوب عمل می‌کند. هیچ وقت مشکلی نداشته‌ام.",
    "من از این فروشگاه بسیار راضیم. همیشه محصولات با کیفیتی را دریافت می‌کنم.",
    "از تجربه خریدم از این فروشگاه بسیار راضی هستم. خدمات شما بسیار حرفه‌ای است.",
    "محصولات شما همیشه با کیفیت و قیمت مناسبی هستند. همیشه از شما خرید می‌کنم.",
    "فروشگاه شما همیشه خوب عمل می‌کند. هیچ وقت مشکلی نداشته‌ام.",
    "من از این فروشگاه بسیار راضیم. همیشه محصولات با کیفیتی را دریافت می‌کنم.",
    "از تجربه خریدم از این فروشگاه بسیار راضی هستم. خدمات شما بسیار حرفه‌ای است.",
    "محصولات شما همیشه با کیفیت و قیمت مناسبی هستند. همیشه از شما خرید می‌کنم.",
    "فروشگاه شما همیشه خوب عمل می‌کند. هیچ وقت مشکلی نداشته‌ام.",
    "من از این فروشگاه بسیار راضیم. همیشه محصولات با کیفیتی را دریافت می‌کنم.",
    "از تجربه خریدم از این فروشگاه بسیار راضی هستم. خدمات شما بسیار حرفه‌ای است.",
    "محصولات شما همیشه با کیفیت و قیمت مناسبی هستند. همیشه از شما خرید می‌کنم.",
    "فروشگاه شما همیشه خوب عمل می‌کند. هیچ وقت مشکلی نداشته‌ام.",
    "من از این فروشگاه بسیار راضیم. همیشه محصولات با کیفیتی را دریافت می‌کنم.",
    "از تجربه خریدم از این فروشگاه بسیار راضی هستم. خدمات شما بسیار حرفه‌ای است.",
    "محصولات شما همیشه با کیفیت و قیمت مناسبی هستند. همیشه از شما خرید می‌کنم.",
    "فروشگاه شما همیشه خوب عمل می‌کند. هیچ وقت مشکلی نداشته‌ام.",
    "من این محصول رو‌قبلا خرید کردم به عنوان کادو و خیلی راضی بودم",
    "من تازه خریدمش و خیلی خفنه خریدشو توصیه میکنم",
    "بهترین انتخاب در این بازه قیمتیست.",
    "خیلی حرفه ای هست و راضی هستم",
    "من راضی هستم و فعلا دارم کارکردن باهاش را یاد میگیرم.",
    "واقعا راضی ام ، کیفیتش فوق العادست.",
    "عالی، پر توان باشید.",
    "به موقع و بسته بندی مناسب در کل عالی بود و سر وقت تحویل گرفتم",
    "عالیه خیلی با کیفیت و خوبه",
    "عالی بود خیلی راضی بودم بخرید پشیمون نمی شوید",
    "حتما خریداری کنید ناراضی نخواهید بود",
    "من داشتم خیلی خوبه",
    "کیفیت و قیمت طبق نظرات سایت بود و مناسب بود",
    "من تازه گرفتمش ، کیفیت خوبی داره و واقعا ازش راضیم، هم قیمتش خوبه هم کاراییش",
    "در یک کلام بی نظیر",
    "نسبت به قیمتش عالیه",
    "ارسال سریع و پشتیبانی عالی , تشکر از تیم دوربین شات",
    "فروشگاهتون حرف نداره",
    "ارسالش سریع بود ولی هزینه ارسالش کم بود",
    "با اینکه تهران نیستم ولی خیلی زود به دستم رسید",
    "من که راضی بودم به شماهم پیشنهادش میکنم",
    "ارسالش سریع بود و کیفیت خیلی خوبی هم داشت",
    "یکی از بهترین محصولای سونی",
    "من که با این دوربین طرفدار سونی شدم",
    "عالیه برای شروع و افراد مبتدی پیشنهادش میکنم",
    "کارایی خوب کیفیت خوب ارسال سریع مرسی ازتون",
    "قبل خرید شک داشتم ولی وقتی تماس گرفتم با تیم پشتیبانی کامل راهنماییم کردن و الان واقعا از خریدم راضیم",
    "سونی مگه محصول بدم داره",
    "مناسب ترین قیمت برای این محصولو اینجا داشت",
    "وقتی خرید کردم کمتر از یروز به دستم رسید و این خیلی برام مهم بود چون عجله داشتم",
    "سه ماه پیش خریدم و الان خواستم اینجا بهتون بگم از خریدنش ضرر نمیکنید بهترینه",
    "قیمتش مناسب بود",
    "با پیشنهاد همکارم خریدم و خیلی راضیم",
    "نسبت به قیمتی که گذاشتید خیلی خوبه",
    "خیلی خوبه ولی به درد افراد مبتدی نمیخوره",
    "من خریدم بنظرم خیلی خوبه",
    "من پنج ماهه دارمش و خیلی راضیم به شما هم پیشنهاد میکنم اگه دو دل هستید از خریدش پشیمون نمیشید",
    "من برای شروع عکاسی خریدم و الان هر سوالی دارم پشتیبانی جوابمو میده",
    "عالی بود",
    "راضیم",
    "خیلی خوب بود",
    "بهترینه",
    "قیمتش پایین بود",
    "قیمتش خیلی مناسبه",
    "خفنه",
    "بنظر من که عالیه",
    "پیشنهاد میشه",
    "خیلی خفنه",
    "من دارمش راضیم",
    "ارزش خریدو داشت",
    "بهترینه بنظرم",
    "پشتیبانی عالی",
    "قیمتش خوب بود",
    "موجودش کنید لطفا",
    "من الان یه ماهه منتظرم موجود شه",
    "عالیه",
    "گاد بود",
    "خیلی خوبه این لامصب",
    "من که خیلی راضیم",
    "راضیم از خریدم",
    "بهترین انتخابه",
    "من تعریفشو زیاد شنیده بودم ولی این خفن تره",
    "واقعا که ارزش قیمتشو داشت",
    "کاراییش نسبت به قیمتش بیشتره",
    "سونی محصول بد نداره کلا",
    "سونی بهترینه",
    "چقدر قیمتش مناسبه",
    "من تو جشنواره خریدم خیلی ارزون بود",
    "منتظرم تخفیف بزارید بخرم"
]
    
    '''
    comments_by_rating = {
    5: [
        "سلام، اینجا واقعا بهترین فروشگاه آنلاینه!",
        "من کاملا از خریدم راضی هستم. ارسال سریع و کیفیت بالا!",
        "با این فروشگاه تجربه خرید بسیاری داشتم و همیشه راضی بودم.",
        "محصولاتشون واقعا خوبه، همیشه از اینجا خرید می‌کنم.",
        "از این فروشگاه خیلی راضیم. همیشه محصولات با کیفیت و به موقع می‌فرستند.",
        "هیچ وقت از این فروشگاه ناراضی نشدم. کاملا توصیه می‌شه!",
        "خریدم از این فروشگاه را به همه پیشنهاد می‌کنم. عالیه!",
        "محصولاتشون واقعاً عالیه، من کاملاً از خریدم راضیم.",
        "با این فروشگاه تجربه خوبی داشتم. کیفیت و قیمت مناسبی دارند.",
        "از این فروشگاه واقعاً راضیم. هیچ وقت مشکلی نداشتم.",
        "من از این فروشگاه خیلی خوشم می‌آد. همیشه به موقع و با کیفیت ارسال می‌کنند.",
        "از تجربه خریدم از این فروشگاه بسیار خوشم آمده. ممنون از شما!",
        "فروشگاه فوق‌العاده‌ایه. هیچگاه ناامید نشده‌ام.",
        "از این فروشگاه واقعا راضی هستم. محصولات با کیفیت و قیمت مناسبی دارند.",
        "محصولاتشون واقعا با کیفیته. هیچ وقت مشکلی نداشتم.",
        "از تجربه خریدم از این فروشگاه بسیار خوشم آمده. حتما به دیگران هم پیشنهاد می‌کنم.",
        "من همیشه از این فروشگاه خرید می‌کنم. هیچ وقت ناامید نشده‌ام.",
        "فروشگاه عالییییه! همیشه کیفیت و قیمت مناسبی دارند.",
        "از این فروشگاه بسیار راضی هستم. تنوع محصولات و خدمات عالی دارند.",
        "من از این فروشگاه خیلی خوشم می‌آد. هیچ وقت مشکلی نداشته‌ام.",
        "تجربه‌ی خوبی داشتم با این فروشگاه. حتما به دوستانم هم پیشنهادش می‌کنم.",
        "از تجربه خریدم از این فروشگاه بسیار راضی هستم. همیشه به موقع و با کیفیت ارسال می‌کنند.",
        "از فروشگاه شما خیلی راضیم. محصولات با کیفیتی دارید.",
        "محصولات فوق‌العاده‌ای دارید. همیشه از شما خرید می‌کنم.",
        "تنوع محصولات واقعا زیاده. هر چیزی که نیاز داشتم اینجا پیدا کردم.",
        "خدمات شما عالیه. همیشه با ارزش‌ترین محصولات را ارائه می‌دهید.",
        "از تجربه خریدم از این فروشگاه بسیار راضی هستم. همیشه محصولات با کیفیتی را دریافت می‌کنم.",
        "فروشگاه شما واقعاً عالیه. همیشه سریع و با کیفیت ارسال می‌کنید.",
        "من از این فروشگاه بسیار راضیم. همیشه محصولات با کیفیتی را دریافت می‌کنم.",
        "از تجربه خریدم از این فروشگاه بسیار راضی هستم. محصولات بسیار با کیفیتی دارید.",
        "فروشگاه شما همیشه عالی عمل می‌کند. هیچ وقت ناامید نشده‌ام.",
        "از تجربه خریدم از این فروشگاه بسیار راضی هستم. خدمات شما بسیار حرفه‌ای است.",
        "محصولات شما همیشه با کیفیت و قیمت مناسبی هستند. همیشه از شما خرید می‌کنم.",
        "فروشگاه شما همیشه خوب عمل می‌کند. هیچ وقت مشکلی نداشته‌ام.",
        "من از این فروشگاه بسیار راضیم. همیشه محصولات با کیفیتی را دریافت می‌کنم.",
        "از تجربه خریدم از این فروشگاه بسیار راضی هستم. خدمات شما بسیار حرفه‌ای است.",
        "محصولات شما همیشه با کیفیت و قیمت مناسبی هستند. همیشه از شما خرید می‌کنم.",
        "فروشگاه شما همیشه خوب عمل می‌کند. هیچ وقت مشکلی نداشته‌ام.",
        "من از این فروشگاه بسیار راضیم. همیشه محصولات با کیفیتی را دریافت می‌کنم.",
        "از تجربه خریدم از این فروشگاه بسیار راضی هستم. خدمات شما بسیار حرفه‌ای است.",
        "محصولات شما همیشه با کیفیت و قیمت مناسبی هستند. همیشه از شما خرید می‌کنم.",
        "فروشگاه شما همیشه خوب عمل می‌کند. هیچ وقت مشکلی نداشته‌ام.",
        "من از این فروشگاه بسیار راضیم. همیشه محصولات با کیفیتی را دریافت می‌کنم.",
        "از تجربه خریدم از این فروشگاه بسیار راضی هستم. خدمات شما بسیار حرفه‌ای است.",
"محصولات شما همیشه با کیفیت و قیمت مناسبی هستند. همیشه از شما خرید می‌کنم.",
"فروشگاه شما همیشه خوب عمل می‌کند. هیچ وقت مشکلی نداشته‌ام.",
"من این محصول رو‌قبلا خرید کردم به عنوان کادو و خیلی راضی بودم",
"من تازه خریدمش و خیلی خفنه خریدشو توصیه میکنم",
"عالی، پر توان باشید.",
"عالیه خیلی با کیفیت و خوبه",
"عالی بود خیلی راضی بودم بخرید پشیمون نمی شوید",
"حتما خریداری کنید ناراضی نخواهید بود",
"در یک کلام بی نظیر",
"ارسال سریع و پشتیبانی عالی , تشکر از تیم دوربین شات",
"فروشگاهتون حرف نداره",
"من که راضی بودم به شماهم پیشنهادش میکنم",
"یکی از بهترین محصولای سونی",
"من که با این دوربین طرفدار سونی شدم",
"عالیه برای شروع و افراد مبتدی پیشنهادش میکنم",
"کارایی خوب کیفیت خوب ارسال سریع مرسی ازتون",
"قبل خرید شک داشتم ولی وقتی تماس گرفتم با تیم پشتیبانی کامل راهنماییم کردن و الان واقعا از خریدم راضیم",
"سونی مگه محصول بدم داره",
"مناسب ترین قیمت برای این محصولو اینجا داشت",
"وقتی خرید کردم کمتر از یروز به دستم رسید و این خیلی برام مهم بود چون عجله داشتم",
"سه ماه پیش خریدم و الان خواستم اینجا بهتون بگم از خریدنش ضرر نمیکنید بهترینه",
"با پیشنهاد همکارم خریدم و خیلی راضیم",
"عالی بود",
"راضیم",
"خیلی خوب بود",
"بهترینه",
"خفنه",
"بنظر من که عالیه",
"پیشنهاد میشه",
"خیلی خفنه",
"من دارمش راضیم",
"ارزش خریدو داشت",
"بهترینه بنظرم",
"پشتیبانی عالی",
"عالیه",
"گاد بود",
"خیلی خوبه این لامصب",
"من که خیلی راضیم",
"راضیم از خریدم",
"بهترین انتخابه",
"من تعریفشو زیاد شنیده بودم ولی این خفن تره",
"واقعا که ارزش قیمتشو داشت",
"کاراییش نسبت به قیمتش بیشتره",
"سونی محصول بد نداره کلا",
"سونی بهترینه",
"چقدر قیمتش مناسبه",
"من تو جشنواره خریدم خیلی ارزون بود",
"خدماتتون حرف نداره",
"راضیم از خریدم",
"بابت این پشتیبانی تبریک میگم بهتون",
"خیلی سریع ارسال شد ممنون",
"من تازه رسیده به دستم خیلی ذوق دارم",
"راضیم واقعا",
"هیچجوره از خریدش پشیمون نمیشید",
"مرسی از فروشگاه خوبتون",
"پشتیبانی بسیار سریع",
"من تو تعطیلی خرید کردم ولی همون روز فرستادن برام",
"مرسی از سایت خوبتون",
"حرف نداره",
"خیلی عالی",
"کیفیتش بی نظریه",
"کاملا عالی مرسی",
"پشتیبانی سریع جواب داد ممنون",
"تجربه خرید خوبی بود",
"کارتون درسته",
"خدماتتون واقعا راضی کنندس",
"خیلی خفنه",
"دقیقا چیزی که لازم داشتم",
"بسیار عالی",
"راضیم , بازم خرید میکنم ازتون",
"من همه جا سایت شمارو معرفی میکنم",
"ارزش خرید داره",
"تحویل به موقع",
"بسته بندی مناسب در کل عالی",
"سر وقت تحویل گرفتم",
"انتخاب عالی برای عکاسان حرفه‌ای",
"خرید آسان",
"ارزش قیمتشو داشت",
"مرسی ازتون",
"بعد از خرید محصول، از کیفیتش خیلی راضیم",
"به عنوان یک عکاس حرفه‌ای، این محصول رو پیشنهاد می‌کنم",
"از خریدم خوشحالم",
"با این تجهیزات عکاسی یه لذت واقعیه",
"تنها کلمه‌ای که دارم اینه: عالی",
"هرچی بگم کمه",
"خرید کردم و واقعا پشیمون نشدم",
"از راهنمایی و پشتیبانی خوبتون ممنونم",
"عالی و با کیفیت",
"امکاناتش عالیه",
"کیفیتش خوبه",
"همه چی تمومه",
"خیلی حرفه ای راضی هستم",
"در کل عالیه",
"واقعا عالیه حتما پیشنهاد میکنم",
"من دارمش خیلی کیفیتش خوبه",
"بهترینه بنظرم",
],
    4: [

"سونی نیاز به تعریف نداره یک کلام عالیه",
"خوب بود و با کیفیت",
"سونی نیاز به تعریف نداره عالیه پیشنهادش میکنم",
"عالیه خوشم اومد",
"راضیم از خریدی که داشتم",
"عالی از هر نظر",
"تو این رنج قیمت خیلی خوبه",
"کیفیتش فوق العادست",
"بسته بندی پلمپ بود همراه با گارانتی",
"واقعا حرفه ایه",
"سونی حرف نداره",
"سونی بی نظیره",
"خیلی عالی و شیکه",
"پیشنهاد میشه",
"با کیفیت و خوبه",
"در یک جمله بگم که عالیه",
"من از اینجا همیشه راضی بودم",
"تجهیزات اینجا واقعا عالین",
"محصولات و خدمات عالی",
"قیمت مناسب",
"من همیشه وبسایت خوبتونو به دوستام معرفی میکنم",
"تجربه خرید بی نظیری بود",
"کیفیت بالا و تحویل به موقع",
"عاشقش شدم , ممنون",
"محصول فوق العادس مرسی ازتون",
"مرسی از پشتیبانی سریع و کاربلدتون",
"باورتون نمیشه چقدر خوبه",
"واقعا سایتتون عالیه",
"پیشنهاد میکنم بخرید",
"جزو بهترین محصولات سونی",
"اصلا پشیمون نمیشید",
"خیلی سریع ارسال شد و هزینش به صرفه بود"
],
    3: [
        "خب، نه خیلی خوب بود نه خیلی بد. یه تجربه متوسط داشتم.",
    "قیمتش مناسب بود اما کیفیت محصول انتظارات منو برآورده نکرد.",
    "سرویس دهی خوبی داشتن اما در کل رضایت کامل نداشتم.",
    "چیزی نبود که بگم وای عالیه، اما در عین حال قابل قبول بود.",
    "تا حدودی راضی بودم اما انتظار بیشتری داشتم.",
    "یکم تاخیر تو ارسال داشتن",
    "فک میکردم بهتر باشه",
    "بد نبود توقعم بیشتر بود",
    "اینجا از همه جا ارزون تر زده دلیلش چیه؟",
    "همش افزایش قیمت داره",
    "چرا موجود نمیشه؟",
    "منتظرم تخفیف بزارید بخرم",
    "لطفا موجودش کنید سریعتر",
    "موجودش کنید لطفا",
    "من الان یه ماهه منتظرم موجود شه",
    "موجود کنین لطفااااا",
    ],

    }'''
    comments_by_rating={
        5 :["عالی ",
        "پنج ستاره کمه",
        "خدماتتون حرف نداره",
        "راضیم از خریدم",
        "بابت این پشتیبانی تبریک میگم بهتون",
        "خیلی سریع ارسال شد ممنون",
        "من تازه رسیده به دستم خیلی ذوق دارم",
        "راضیم واقعا",
        "هیچجوره از خریدش پشیمون نمیشید",
        "مرسی از فروشگاه خوبتون",
        "پشتیبانی بسیار سریع",
        "من تو تعطیلی خرید کردم ولی همون روز فرستادن برام ",
        "مرسی از سایت خوبتون",
        "حرف نداره",
        "خیلی عالی",
        "کیفیتش بی نظریه ",
        "کاملا عالی مرسی",
        "پشتیبانی سریع جواب داد ممنون",
        "تجربه خرید خوبی بود",
        "کارتون درسته",
        "خدماتتون واقعا راضی کنندس",
        "خیلی خفنه",
        "دقیقا چیزی که لازم داشتم",
        "بسیار عالی",
        "راضیم ",
        "بازم خرید میکنم ازتون",
        "من همه جا سایت شمارو معرفی میکنم",
        "ارزش خرید داره",
        "تحویل به موقع",
        "لطفا موجودش کنید سریعتر",
        "بسته بندی مناسب در کل عالی",
        "سر وقت تحویل گرفتم",
        "انتخاب عالی برای عکاسان حرفه‌ای",
        "خرید آسان",
        "ارزش قیمتشو داشت",
        "مرسی ازتون",
        "بعد از خرید محصول، از کیفیتش خیلی راضیم",
        "به عنوان یک عکاس حرفه‌ای، این محصول رو پیشنهاد می‌کنم",
        "از خریدم خوشحالم",
        "با این تجهیزات عکاسی یه لذت واقعیه",
        "تنها کلمه‌ای که دارم اینه: عالی",
        "هرچی بگم کمه",
        "خرید کردم و واقعا پشیمون نشدم",
        "از راهنمایی و پشتیبانی خوبتون ممنونم",
        "موجودش کنید",
        "عالی و با کیفیت",
        "امکاناتش عالیه",
        "کیفیتش خوبه",
        "همه چی تمومه",
        "خیلی حرفه ای راضی هستم",
        "در کل عالیه ",
        "واقعا عالیه حتما پیشنهاد میکنم",
        "من دارمش خیلی کیفیتش خوبه",
        "بهترینه بنظرم",
        "موجود کنین لطفااااا",
        "من سه ماه پیش خریدم راضیم",
        "سونی نیاز به تعریف نداره یک کلام عالیه",
        "خوب بود و با کیفیت",
        "سونی نیاز به تعریف نداره عالیه پیشنهادش میکنم",
        "عالیه خوشم اومد",
        "راضیم از خریدی که داشتم",
        "عالی از هر نظر",
        "تو این رنج قیمت خیلی خوبه",
        "کیفیتش فوق العادست",
        "بسته بندی پلمپ بود همراه با گارانتی",
        "واقعا حرفه ایه",
        "سونی حرف نداره",
        "سونی بی نظیره",
        "یکم تاخیر تو ارسال داشتن",
        "چرا موجود نمیشه؟",
        "فک میکردم بهتر باشه",
        "بد نبود توقعم بیشتر بود",
        "عالی",
        "اینجا از همه جا ارزون تر زده دلیلش چیه؟",
        "همش افزایش قیمت داره",
        "خیلی عالی و شیکه",
        "پیشنهاد میشه",
        "با کیفیت و خوبه",
        "در یک جمله بگم که عالیه",
        "من از اینجا همیشه راضی بودم",
        "تجهیزات اینجا واقعا عالین",
        "محصولات و خدمات عالی",
        "قیمت مناسب",
        "من همیشه وبسایت خوبتونو به دوستام معرفی میکنم",
        "تجربه خرید بی نظیری بود",
        "کیفیت بالا و تحویل به موقع",
        "عاشقش شدم" ,
        "ممنون",
        "محصول فوق العادس مرسی ازتون",
        "مرسی از پشتیبانی سریع و کاربلدتون",
        "باورتون نمیشه چقدر خوبه",
        "واقعا سایتتون عالیه",
        "پیشنهاد میکنم بخرید",
        "جزو بهترین محصولات سونی",
        "اصلا پشیمون نمیشید",
        "خیلی سریع ارسال شد و هزینش به صرفه بود",
        "کیفیت تصویر عالی",
        "کیفیت تصویر این دوربین واقعا عالیه، حتی در نور کم هم عکس‌های بی‌نظیری می‌گیره.",
        "فوکوس سریع و دقیقی داره که کار عکس‌برداری رو خیلی راحت‌تر کرده.",
        "طراحی زیبا و مدرنش باعث شده همیشه بخوام ازش استفاده کنم.",
        "عمر باتریش طولانیه و می‌تونم با خیال راحت در طول روز عکاسی کنم.",
        "ضبط ویدیو با کیفیت بالای این دوربین واقعا منو شگفت‌زده کرده.",
        "کنترل‌هاش خیلی کاربرپسند هستن و تنظیماتش خیلی آسونه.",
        "وزنش سبک و قابل حمله، برای سفر خیلی مناسبه.",
        "قابلیت اتصال به وای‌فای خیلی کاربردیه، عکس‌ها رو سریع می‌تونم انتقال بدم.",
        "تنظیمات متنوع و گسترده‌ای داره که به من اجازه می‌ده عکس‌های خلاقانه‌ای بگیرم.",
        "این دوربین در شرایط آب و هوایی مختلف خیلی خوب کار می‌کنه، واقعا مقاومه.",
        "صفحه نمایش لمسی و واضحش خیلی کمک می‌کنه که عکس‌ها رو بهتر ببینم و تنظیمات رو راحت‌تر انجام بدم.",
        "سرعت بالا در عکس‌برداری پیاپی باعث شده هیچ لحظه‌ای رو از دست ندم.",
        "لنز‌های قابل تعویضش واقعا کاربردی هستن و باعث می‌شن عکس‌های متنوعی بگیرم.",
        "عملکردش در نور کم عالیه و عکس‌های خیلی خوبی می‌گیره.",
        "پردازنده‌ی سریع و قدرتمندش باعث شده هیچ تاخیری در عکاسی نداشته باشم.",
        "نرم‌افزار همراهش خیلی کاربردیه و به راحتی می‌تونم عکس‌ها رو ویرایش و به اشتراک بذارم.",
        "قیمتش نسبت به کیفیتی که ارائه می‌ده واقعا مناسبه.",
        "شاتر بی‌صدا و نرمش خیلی خوبه و می‌تونم در مکان‌های آرام هم عکاسی کنم.",
        "قابلیت عکس‌برداری پانوراما به من اجازه می‌ده که مناظر زیبا رو به طور کامل ثبت کنم.",
        "سازگاریش با لوازم جانبی مختلف باعث شده بتونم از تجهیزات دیگه‌ام هم استفاده کنم.",
        "بدنه‌ی مقاوم و محکمی داره که در سفرهای ماجراجویانه خیلی خوبه.",
        "سیستم لرزشگیرش کارآمده و عکس‌های بدون لرزشی می‌گیرم.",
        "حسگر بزرگ و با کیفیتش باعث می‌شه عکس‌ها جزئیات بیشتری داشته باشن.",
        "کیفیت ساخت این دوربین عالیه و حس می‌کنم محصولی بسیار حرفه‌ای دستم دارم.",
        "امکان عکاسی در حالت دستی واقعا خوبه و می‌تونم تنظیمات رو دقیق‌تر انجام بدم.",
        "قابلیت ارسال مستقیم به شبکه‌های اجتماعی کارم رو خیلی راحت کرده.",
        "تنظیمات خودکار هوشمندش باعث می‌شه همیشه عکس‌های خوبی بگیرم.",
        "پشتیبانی از فرمت RAW برای ویرایش حرفه‌ای عکس‌ها خیلی مهمه.",
        "دید عالی از طریق منظره‌یاب دارم و می‌تونم بهتر کادربندی کنم.",
        "امکان عکس‌برداری تایم‌لپس باعث شده ویدیوهای خلاقانه‌ای بسازم.",
        "قابلیت تشخیص چهره خیلی خوب عمل می‌کنه و عکس‌های پرتره عالی می‌گیرم.",
        "عکس‌ها با جزئیات دقیق و وضوح بالا هستن، خیلی راضیم.",
        "عملکرد بی‌نظیرش در عکاسی ورزشی باعث شده لحظات مهم رو از دست ندم.",
        "حالت‌های عکاسی متنوعش به من اجازه می‌ده در شرایط مختلف بهترین عکس رو بگیرم.",
        "نرم‌افزار ویرایش عکس همراهش خیلی کاربردیه و می‌تونم عکس‌ها رو به راحتی ویرایش کنم.",
        "نمایشگر چرخانش خیلی کمک می‌کنه که از زوایای مختلف عکاسی کنم.",
        "ذخیره‌سازی سریع عکس‌ها باعث شده هیچ وقت منتظر نمونم.",
        "کاربری آسانش حتی برای مبتدی‌ها هم مناسبه.",
        "راهنمای کاربری مفصل و جامعش باعث شده به راحتی با تمام امکاناتش آشنا بشم.",
        "قابلیت اتصال بلوتوث خیلی کاربردیه و سریع عکس‌ها رو به گوشی منتقل می‌کنم.",
        "طراحی ارگونومیکش باعث شده دستم خسته نشه.",
        "کیفیت صدای ضبط شده در ویدیوهاش عالیه.",
        "عملکرد خوبش در عکاسی ماکرو باعث شده عکس‌های خیلی نزدیکی بگیرم.",
        "قابلیت عکس‌برداری HDR رنگ‌ها رو خیلی طبیعی و زیبا می‌کنه.",
        "امکان تنظیمات پیشرفته برای حرفه‌ای‌ها خیلی خوبه و می‌تونم دقیقا همون عکسی که می‌خوام رو بگیرم.",
        "رزولوشن بالا باعث شده عکس‌ها خیلی واضح باشن.",
        "شارژ سریعش خیلی خوبه و همیشه آماده عکاسی هستم.",
        "بازه‌ی دینامیکی وسیعش باعث شده عکس‌ها خیلی طبیعی باشن.",
        "رنگ‌های طبیعی و زیباش واقعا چشم‌نوازه.",
        "سنسور با عملکرد سریعش هیچ لحظه‌ای رو از دست نمی‌ده.",
        "دکمه‌های کاربردی و در دسترسش باعث شده سریع به تنظیمات دسترسی داشته باشم.",
        "لنز با دیافراگم بازش عکس‌های خیلی خوبی در نور کم می‌گیره.",
        "تطبیق‌پذیری بالاش با شرایط مختلف نوری خیلی خوبه.",
        "کیفیت بالای فایل‌های خروجیش باعث شده عکس‌ها رو راحت‌تر ویرایش کنم.",
        "امکانات گسترده‌ی ارتباطیش خیلی کاربردیه.",
        "تصاویر بدون نویزش واقعا چشم‌نوازه.",
        "امکان استفاده از فیلترهای متنوعش باعث شده عکس‌های خلاقانه‌تری بگیرم.",
        "سرعت بالاش در پردازش تصاویر خیلی خوبه و هیچ وقت منتظر نمونم.",
        "عملکرد سریعش در روشن شدن باعث شده هیچ لحظه‌ای رو از دست ندم.",
        "کیفیت ساخت فوق‌العاده‌ای داره و حس می‌کنم محصولی با دوام دستمه.",
        "راه‌اندازی آسونش خیلی خوبه و سریع می‌تونم شروع به عکاسی کنم.",
        "تصویر واضح در حالت زوم خیلی خوبه و جزئیات رو بهتر می‌بینم.",
        "قابلیت عکاسی در شبش باعث شده عکس‌های خوبی در تاریکی بگیرم.",
        "تثبیت کننده تصویر اپتیکالش باعث شده عکس‌های بدون لرزشی بگیرم.",
        "امکان ذخیره‌سازی ابری تصاویر خیلی کاربردیه و دیگه نگران از دست دادن عکس‌ها نیستم.",
        "نرم‌افزار همراه کاربرپسندش خیلی خوبه و راحت می‌تونم عکس‌ها رو ویرایش کنم.",
        "حالت‌های عکاسی خلاقانه‌اش به من اجازه می‌ده عکس‌های منحصر به فردی بگیرم.",
        "ضبط ویدیو با کیفیت 4K واقعا عالیه و ویدیوها خیلی واضح هستن.",
        "سازگاریش با برنامه‌های موبایل خیلی خوبه و به راحتی می‌تونم عکس‌ها رو انتقال بدم.",
        "امکان عکس‌برداری خودکار با تایمر خیلی کاربردیه و برای عکس‌های گروهی عالیه.",
        "تصاویر با وضوح بالاش باعث شده هر جزئیاتی رو ثبت کنم.",
        "سیستم فوکوس خودکار پیشرفته‌اش خیلی خوبه و همیشه عکس‌های شفافی دارم.",
        "عکس‌های با رنگ‌های طبیعی واقعا زیبا هستن.",
        "قابلیت ضبط صدای استریو در ویدیوهاش خیلی خوبه.",
        "منظره‌یاب بزرگ و روشنش باعث شده بهتر کادربندی کنم.",
        "امکان اتصال USB خیلی کاربردیه و می‌تونم سریع عکس‌ها رو انتقال بدم.",
        "عملکرد خوبش در حالت پرتره باعث شده عکس‌های زیبایی بگیرم.",
        "عکس‌برداری سریع بدون تاخیرش باعث شده هیچ لحظه‌ای رو از دست ندم.",
        "به‌روز رسانی‌های منظم نرم‌افزاریش باعث شده همیشه بهترین عملکرد رو داشته باشه.",
        "تنظیمات ISO متنوعش به من اجازه می‌ده در شرایط نوری مختلف عکس‌های خوبی بگیرم.",
        "کیفیت تصویر بالا حتی در شرایط نور کم واقعا عالیه.",
        "راهنمای تنظیمات خودکارش خیلی خوبه و همیشه بهترین تنظیمات رو پیشنهاد می‌ده.",
        "نرم‌افزار کاربردی برای انتقال عکس‌ها خیلی کمک کرده که سریع عکس‌ها رو به اشتراک بذارم.",
        "وزن مناسبش برای عکاسی طولانی مدت خیلی خوبه و دستم خسته نمی‌شه.",
        "قابلیت تنظیم تراز سفیدی خیلی خوبه و باعث شده رنگ‌ها دقیق‌تر باشن.",
        "دسترسی سریع به تنظیمات مهم باعث شده هیچ وقت منتظر نمونم.",
        "عملکرد بی‌نقصش در حالت‌های مختلف باعث شده همیشه عکس‌های خوبی بگیرم.",
        "خروجی رنگ‌های زنده و جذابش واقعا زیبا هستن.",
        "سنسور با حساسیت بالاش باعث شده هیچ لحظه‌ای رو از دست ندم.",
        "کیفیت بی‌نظیر تصاویر در فرمت RAW باعث شده عکس‌ها رو حرفه‌ای ویرایش کنم.",
        "تنظیمات نوردهی دقیقش باعث شده همیشه عکس‌های خوبی بگیرم.",
        "قابلیت اتصال به سه‌پایه خیلی کاربردیه و برای عکس‌های ثابت عالیه.",
        "نمایشگر با کیفیت و روشنش خیلی خوبه و عکس‌ها رو واضح می‌بینم.",
        "امکان استفاده از کارت‌های حافظه مختلف خیلی خوبه و همیشه فضای کافی دارم.",
        "عملکرد خوبش در عکاسی خیابانی باعث شده لحظات روزمره رو به خوبی ثبت کنم.",
        "قابلیت ضبط ویدیو با نرخ فریم بالا خیلی خوبه و ویدیوها روان هستن.",
        "طراحی شیک و مدرنش باعث شده همیشه بخوام ازش استفاده کنم.",
        "قابلیت تشخیص اشیا خیلی خوبه و عکس‌های دقیقی می‌گیرم.",
        "امکان مدیریت فایل‌های ذخیره شده خیلی خوبه و همیشه عکس‌هام مرتب هستن.",
        "عکس‌های با کیفیت و حرفه‌ایش باعث شده همیشه به عکاسی علاقه‌مند باشم.",
        ] ,
        4 : [
            "عکس‌های با رنگ‌های واقعی",
        "امکان عکاسی با تایمر",
        "کنترل از راه دور",
        "کیفیت عالی در حالت پرتره",
        "تصاویر با وضوح بالا",
        "ضبط ویدیو با صدای استریو",
        "تنظیمات خودکار هوشمند",
        "منظره‌یاب الکترونیکی شفاف",
        "ذخیره‌سازی سریع تصاویر",
        "نمایشگر چرخان و قابل تنظیم",
        "دکمه‌های کاملا در دسترس",
        "پشتیبانی از کارت حافظه",
        "کیفیت ساخت بی‌نظیر",
        "تصاویر بدون نویز",
        "تثبیت‌کننده تصویر دیجیتال",
        "تنظیمات ISO متنوع",
        "سازگاری با اپلیکیشن‌های موبایل",
        "قابلیت عکاسی ماکرو",
        "پشتیبانی از فرمت JPEG",
        "تنظیمات پیشرفته نوردهی",
        "خروجی عکس‌های باکیفیت",
        "حالت عکاسی سیاه‌وسفید",
        "عکاسی در شب عالی",
        "اتصال NFC سریع",
        "امکان استفاده از فلاش",
        "کنترل دستی دیافراگم",
        "پشتیبانی از تایم‌لپس",
        "سنسور فول‌فریم",
        "ذخیره‌سازی ابری تصاویر",
        "عکاسی با سرعت بالا",
        "قابلیت اتصال HDMI",
        "فیلم‌برداری با کیفیت 1080p",
        "عکس‌برداری بی‌وقفه",
        "تثبیت‌کننده تصویر اپتیکال",
        "لنز واید زاویه باز",
        "کیفیت عالی در زوم",
        "کنترل تنظیمات با اپلیکیشن",
        "صفحه نمایش باکیفیت",
        "عکس‌برداری سریع و آسان",
        "قابلیت عکاسی HDR",
        "عکس‌های حرفه‌ای و جذاب",
        "تنظیمات پیشرفته فوکوس",
        "قابلیت اتصال به سه‌پایه",
        "کیفیت عالی در پرتره",
        "پشتیبانی از فیلترهای مختلف",
        "عکاسی با کیفیت در روز",
        "منوی کاربری ساده",
        "نرم‌افزار ویرایش حرفه‌ای",
        "ضد آب و ضد گردوغبار",
        "قابلیت تصویربرداری ۳۶۰ درجه",
        "صفحه نمایش رنگی",
        "کنترل شاتر با صدا",
        "پشتیبانی از کارت SD",
        "خروجی ویدیو با کیفیت",
        "کیفیت ساخت مقاوم",
        "عکاسی بدون تاخیر",
        "لنز تله‌فوتو قدرتمند",
        "فیلم‌برداری با نرخ فریم بالا",
        "سنسور پیشرفته و دقیق",
        "عکاسی ورزشی عالی",
        "عکس‌های با جزئیات بالا",
        "قابلیت اتصال به بلوتوث",
        "دسترسی سریع به تنظیمات",
        "بدنه‌ای سبک و مقاوم",
        "عکاسی خودکار حرفه‌ای",
        "ذخیره‌سازی در حافظه داخلی",
        "تصویر با کیفیت در زوم",
        "امکان استفاده از مونوپاد",
        "تصاویر با وضوح واقعی",
        "پشتیبانی از USB-C",
        "خروجی RAW و JPEG",
        "صفحه نمایش ضد بازتاب",
        "عکاسی حرفه‌ای در استودیو",
        "قابلیت عکاسی پیاپی",
        "حالت عکاسی پر سرعت",
        "کیفیت بالا در نور کم",
        "تصویر واضح در زوم",
        "عکاسی با فرمت RAW",
        "قابلیت عکاسی چندگانه",
        "فیلم‌برداری با وضوح 4K",
        "نمایشگر لمسی حساس",
        "لنز باکیفیت و دقیق",
        "فیلم‌برداری در شب",
        "عکاسی حرفه‌ای و سریع",
        "امکان اتصال به وای‌فای",
        "ذخیره‌سازی سریع و آسان"
        "فوکوس سریع و دقیق",
        "طراحی زیبا و مدرن",
        "عمر باتری طولانی",
        "قابلیت ضبط ویدیو با کیفیت بالا",
        "کنترل‌های کاربرپسند",
        "وزن سبک و قابل حمل",
        "قابلیت اتصال به وای‌فای",
        "تنظیمات متنوع و گسترده",
        "مقاومت در برابر شرایط آب و هوایی مختلف",
        "صفحه نمایش لمسی و واضح",
        "سرعت بالا در عکس‌برداری پیاپی",
        "لنز‌های قابل تعویض",
        "عملکرد خوب در نور کم",
        "پردازنده‌ی سریع و قدرتمند",
        "نرم‌افزار همراه کاربردی",
        "قیمت مناسب نسبت به کیفیت",
        "شاتر بی‌صدا و نرم",
        "قابلیت عکس‌برداری پانوراما",
        "سازگاری با لوازم جانبی مختلف",
        "بدنه‌ی مقاوم و محکم",
        "سیستم لرزشگیر کارآمد",
        "حسگر بزرگ و با کیفیت",
        "کیفیت ساخت عالی",
        "امکان عکاسی در حالت دستی",
        "قابلیت ارسال مستقیم به شبکه‌های اجتماعی",
        "تنظیمات خودکار هوشمند",
        "پشتیبانی از فرمت RAW",
        "دید عالی از طریق منظره‌یاب",
        "امکان عکس‌برداری تایم‌لپس",
        "قابلیت تشخیص چهره",
        "عکس‌های با جزئیات دقیق",
        "عملکرد بی‌نظیر در عکاسی ورزشی",
        "حالت‌های عکاسی متنوع",
        "نرم‌افزار ویرایش عکس همراه",
        "نمایشگر چرخان",
        "ذخیره‌سازی سریع عکس‌ها",
        "کاربری آسان حتی برای مبتدی‌ها",
        "راهنمای کاربری مفصل و جامع",
        "قابلیت اتصال بلوتوث",
        "طراحی ارگونومیک",
        "کیفیت صدای ضبط شده عالی",
        "عملکرد خوب در عکاسی ماکرو",
        "قابلیت عکس‌برداری HDR",
        "امکان تنظیمات پیشرفته برای حرفه‌ای‌ها",
        "رزولوشن بالا",
        "شارژ سریع",
        "بازه‌ی دینامیکی وسیع",
        "رنگ‌های طبیعی و زیبا",
        "سنسور با عملکرد سریع",
        "دکمه‌های کاربردی و در دسترس",
        "لنز با دیافراگم باز",
        "تطبیق‌پذیری بالا با شرایط مختلف نوری",
        "کیفیت بالای فایل‌های خروجی",
        "امکانات گسترده‌ی ارتباطی",
        "تصاویر بدون نویز",
        "امکان استفاده از فیلترهای متنوع",
        "سرعت بالا در پردازش تصاویر",
        "عملکرد سریع در روشن شدن",
        "کیفیت ساخت فوق‌العاده",
        "راه‌اندازی آسان",
        "تصویر واضح در حالت زوم",
        "قابلیت عکاسی در شب",
        "تثبیت کننده تصویر اپتیکال",
        "امکان ذخیره‌سازی ابری تصاویر",
        "نرم‌افزار همراه کاربرپسند",
        "حالت‌های عکاسی خلاقانه",
        "ضبط ویدیو با کیفیت 4K",
        "سازگاری با برنامه‌های موبایل",
        "امکان عکس‌برداری خودکار با تایمر",
        "تصاویر با وضوح بالا",
        "سیستم فوکوس خودکار پیشرفته",
        "عکس‌های با رنگ‌های طبیعی",
        "قابلیت ضبط صدای استریو",
        "منظره‌یاب بزرگ و روشن",
        "امکان اتصال USB",
        "عملکرد خوب در حالت پرتره",
        "عکس‌برداری سریع بدون تاخیر",
        "به‌روز رسانی‌های منظم نرم‌افزاری",
        "تنظیمات ISO متنوع",
        "کیفیت تصویر بالا حتی در شرایط نور کم",
        "راهنمای تنظیمات خودکار",
        "نرم‌افزار کاربردی برای انتقال عکس‌ها",
        "وزن مناسب برای عکاسی طولانی مدت",
        "قابلیت تنظیم تراز سفیدی",
        "دسترسی سریع به تنظیمات مهم",
        "عملکرد بی‌نقص در حالت‌های مختلف",
        "خروجی رنگ‌های زنده و جذاب",
        "سنسور با حساسیت بالا",
        "کیفیت بی‌نظیر تصاویر در فرمت RAW",
        "تنظیمات نوردهی دقیق",
        "قابلیت اتصال به سه‌پایه",
        "نمایشگر با کیفیت و روشن",
        "امکان استفاده از کارت‌های حافظه مختلف",
        "عملکرد خوب در عکاسی خیابانی",
        "قابلیت ضبط ویدیو با نرخ فریم بالا",
        "طراحی شیک و مدرن",
        "قابلیت تشخیص اشیا",
        "امکان مدیریت فایل‌های ذخیره شده",
        "عکس‌های با کیفیت و حرفه‌ای",]}
    for i in range(1,random.randint(4,7)):
        rnd_rate =random_rating()
        comment = comments_by_rating[rnd_rate].pop(random.randint(0,len(comments_by_rating[rnd_rate])-1))
        name = names.pop(random.randint(0,len(names)-1))
        data = {
        "product_id": product_id,
        "review": comment,
        "reviewer": name,
        "reviewer_email": "example@example.com",
        "rating":rnd_rate,
        'verified' : True,
        "date_created": random_date()
        }
        response = requests.post(endpoint, headers = woocomerce_login(), json=data)
        logger.info(f'{product_id} : {comment}')
    return response.json()


