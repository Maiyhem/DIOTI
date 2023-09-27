from django.urls import path
from . import views

urlpatterns = [

    path('', views.index, name='product_list'),
    path('product-list/', views.product_list, name='product-list'),
    path('web-prices/', views.web_update_all_prices, name='web-prices'),

    path('scrape_prices/', views.scrap_update_all_prices, name='scrape_prices'),

    path('update-product-list/', views.update_product_list, name='update-product-list'),
]
