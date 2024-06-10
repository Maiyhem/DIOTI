import requests
from .models import Product, Category, Tag, Image
from price_scrapper.views import woocomerce_login  # Replace with the actual module containing your login function

def get_web_product_list(request):
    base_url = 'https://doorbinshot.com/wp-json/wc/v3'
    endpoint = '/products'
    page = 1  # Start with the first page of results
    per_page = 100  # Adjust per_page as needed to retrieve a larger number of products per page

    products = []
    headers = woocomerce_login()

    while True:
        url = f'{base_url}{endpoint}?per_page={per_page}&page={page}'

        params = {"page": page}

        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            # Parse the JSON response and insert products into Django models
            current_page_products = response.json()

            for product_data in current_page_products:
                # Extract relevant information from the API response
                product_id = product_data.get('id')
                name = product_data.get('name')
                # Extract other fields similarly

                # Create or update Product model instance
                product, created = Product.objects.update_or_create(
                    id=product_id,
                   defaults={
                        'name': product_data.get('name', ''),
                        'description': product_data.get('description', ''),
                        'price': product_data.get('price', 0.0),
                        'stock_quantity': product_data.get('stock_quantity', 0),
                        'regular_price': product_data.get('regular_price', 0.0),
                        'sale_price': product_data.get('sale_price', 0.0),
                        'sku': product_data.get('sku', ''),
                        'weight': product_data.get('weight', 0.0),
                        'dimensions': product_data.get('dimensions', ''),
                        'categories': product_data.get('categories', []),
                        'tags': product_data.get('tags', []),
                        
                       }
                )

                # Insert related data (categories, tags, images)
                for category_data in product_data.get('categories', []):
                    Category.objects.get_or_create(
                        product=product,
                        category_id=category_data.get('id'),
                        category_name=category_data.get('name'),
                        category_slug=category_data.get('slug'),
                    )

                for tag_name in product_data.get('tags', []):
                    Tag.objects.get_or_create(
                        product=product,
                        tag_name=tag_name,
                    )

                for image_data in product_data.get('images', []):
                    Image.objects.get_or_create(
                        product=product,
                        image_id=image_data.get('id'),
                        image_src=image_data.get('src'),
                        image_alt=image_data.get('alt'),
                    )

            # Check if there are more pages
            if len(current_page_products) < per_page:
                break
            else:
                page += 1
        else:
            print(f"Failed to retrieve products. Error: {response.text}")
            break

    print("Products inserted into Django models.")
