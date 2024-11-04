from django.urls import path
from . import views
urlpatterns = [
    path('shop_page/', views.shop_page, name='shop_page'),
    path('single_detail/<int:pk>', views.single_detail, name='single_detail'),
]
