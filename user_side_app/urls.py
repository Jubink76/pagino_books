from django.urls import path
from . import views
urlpatterns = [
    path('shop_page/', views.shop_page, name='shop_page'),
    path('single_detail/<int:pk>/', views.single_detail, name='single_detail'),
    path('single_category/<int:pk>/', views.single_category, name='single_category'),
    path('cart_page/',views.cart_page,name='cart_page'),
    path('add_to_cart/<int:book_id>/',views.add_to_cart,name='add_to_cart'),
    path('delete_cart_item/<int:item_id>/',views.delete_cart_item, name='delete_cart_item'),
    path('update_cart_quantity/<int:item_id>/', views.update_cart_quantity, name='update_cart_quantity'),
    path('whishlist_page/',views.whishlist_page,name='whishlist_page'),
    path('add_to_whishlist/<int:book_id>/',views.add_to_whishlist,name='add_to_whishlist'),
    path('delete_whishlist_item/<int:book_id>/',views.del_whishlist_item,name='delete_whishlist_item'),
    path('checkout_page/',views.checkout_page,name='checkout_page'),
    path('checkout_add_address/', views.checkout_add_address, name='checkout_add_address'),
    path('order-success/<str:order_id>/',views.order_success,name='order_success')
]
