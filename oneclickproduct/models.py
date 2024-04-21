
from django.db import models

class Product(models.Model):
    id = models.PositiveIntegerField(primary_key=True)
    name = models.CharField(max_length=255)
    slug = models.SlugField()
    permalink = models.URLField()
    date_created = models.DateTimeField()
    date_created_gmt = models.DateTimeField()
    date_modified = models.DateTimeField()
    date_modified_gmt = models.DateTimeField()
    type = models.CharField(max_length=20)
    status = models.CharField(max_length=20)
    featured = models.BooleanField()
    catalog_visibility = models.CharField(max_length=20)
    description = models.TextField()
    short_description = models.TextField()
    sku = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    regular_price = models.DecimalField(max_digits=10, decimal_places=2)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2)
    date_on_sale_from = models.DateTimeField(null=True, blank=True)
    date_on_sale_from_gmt = models.DateTimeField(null=True, blank=True)
    date_on_sale_to = models.DateTimeField(null=True, blank=True)
    date_on_sale_to_gmt = models.DateTimeField(null=True, blank=True)
    on_sale = models.BooleanField()
    purchasable = models.BooleanField()
    total_sales = models.PositiveIntegerField()
    virtual = models.BooleanField()
    downloadable = models.BooleanField()
    download_limit = models.IntegerField()
    download_expiry = models.IntegerField()
    external_url = models.URLField()
    button_text = models.CharField(max_length=50)
    tax_status = models.CharField(max_length=20)
    tax_class = models.CharField(max_length=20)
    manage_stock = models.BooleanField()
    stock_quantity = models.IntegerField()
    backorders = models.CharField(max_length=20)
    backorders_allowed = models.BooleanField()
    backordered = models.BooleanField()
    low_stock_amount = models.IntegerField()
    sold_individually = models.BooleanField()
    weight = models.CharField(max_length=20)
    length = models.CharField(max_length=20)
    width = models.CharField(max_length=20)
    height = models.CharField(max_length=20)
    shipping_required = models.BooleanField()
    shipping_taxable = models.BooleanField()
    shipping_class = models.CharField(max_length=20)
    shipping_class_id = models.PositiveIntegerField()
    reviews_allowed = models.BooleanField()
    average_rating = models.FloatField()
    rating_count = models.PositiveIntegerField()
    price_html = models.TextField()
    stock_status = models.CharField(max_length=20)
    has_options = models.BooleanField()
    post_password = models.CharField(max_length=20)
    yoast_head = models.TextField()

    # Custom fields
    store_id = models.PositiveIntegerField()
    store_name = models.CharField(max_length=255)
    shop_name = models.CharField(max_length=255)
    shop_url = models.URLField()
    shop_address_street_1 = models.CharField(max_length=255)
    shop_address_street_2 = models.CharField(max_length=255)
    shop_address_city = models.CharField(max_length=255)
    shop_address_zip = models.CharField(max_length=20)
    shop_address_country = models.CharField(max_length=50)
    shop_address_state = models.CharField(max_length=50)

    class Meta:
        verbose_name = 'Product'
        verbose_name_plural = 'Products'

class Category(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    category_id = models.PositiveIntegerField()
    category_name = models.CharField(max_length=255)
    category_slug = models.SlugField()

    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'

class Tag(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    tag_name = models.CharField(max_length=255)

    class Meta:
        verbose_name = 'Tag'
        verbose_name_plural = 'Tags'

class Image(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    image_id = models.PositiveIntegerField()
    image_src = models.URLField()
    image_alt = models.CharField(max_length=255)

    class Meta:
        verbose_name = 'Image'
        verbose_name_plural = 'Images'
