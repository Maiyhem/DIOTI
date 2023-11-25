from django.urls import path
from . import views

urlpatterns = [

   path('logs/', views.logs, name='logs'),
   path('home/', views.home, name='home'),
   path('dashboard/', views.dashboard, name='dashboard'),
    path('', views.index, name='product_list'),
    path('product-list/', views.product_list, name='product-list'),
    path('web-prices/', views.web_update_all_prices, name='web-prices'),

    path('update_product/', views.update_product, name='update_product'),
    path('scrape_prices/', views.scrap_update_all_prices, name='scrape_prices'),
    path('scrape_done/', views.scrape_done, name='scrape_done'),
    path('get_exchange_rate/', views.get_exchange_rate, name='get_exchange_rate'),

    path('ajax-update-target-link/', views.update_product_targetlink, name='ajax-update-target-link'),

    path('update-product-list/', views.update_product_list, name='update-product-list'),
]
