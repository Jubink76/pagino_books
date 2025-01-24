from django.urls import path
from . import views
urlpatterns = [
    path('user_profile/', views.user_profile,name='user_profile'),
    path('user_address/',views.user_address,name='user_address'),
    path('add_address/',views.add_address,name='add_address'),
    path('set-default-address/<int:address_id>/', views.set_default_address, name='set_default_address'),
    path('delete-address/<int:address_id>/', views.delete_address, name='delete_address'),
    path('edit_address/<int:address_id>/',views.edit_address, name='edit_address'),
    path('user_orders/',views.user_orders,name='user_orders'),
    path('user_password_reset',views.user_password_reset,name='user_password_reset'),
    path('user_order_detail/<str:order_id>/', views.user_orders, name='user_order_detail'),
    path('user_wallet',views.user_wallet,name='user_wallet'),
    path('wallet/add-money/paypal/', views.add_money_via_paypal, name='add_money_via_paypal'),
    path('wallet/paypal-success/', views.paypal_success, name='paypal_success'),
    path('wallet/paypal-cancel/', views.paypal_cancel, name='paypal_cancel'),
    path('user_coupon',views.user_coupon,name='user_coupon'),
]