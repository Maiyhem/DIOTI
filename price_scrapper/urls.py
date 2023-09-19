from django.urls import path
from . import views

urlpatterns = [
    path('product_list/', views.product_list, name='product_list'),
    path('scrape_prices/', views.scrape_prices, name='scrape_prices'),
    path('update_prices/', views.update_prices, name='update_prices'),
]