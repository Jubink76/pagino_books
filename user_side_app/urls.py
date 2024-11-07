from django.urls import path
from . import views
urlpatterns = [
    path('shop_page/', views.shop_page, name='shop_page'),
    path('single_detail/<int:pk>/', views.single_detail, name='single_detail'),
    path('single_category/<int:pk>/', views.single_category, name='single_category'),
    path('cart_page/<int:pk>/',views.cart_page,name='cart_page'),
    path('whishlist_page/',views.whishlist_page,name='whishlist_page')
]
