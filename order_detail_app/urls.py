from django.urls import path
from . import views
urlpatterns = [
    path('create-order/',views.create_order,name='create-order'),
    path('cancel_order/<str:order_id>/', views.cancel_order, name='cancel_order'),
    path('user_orders/<str:order_id>/item/<int:order_item_id>/cancel/', views.user_single_item_cancel, name='user_single_item_cancel'),
    #path('return_order/<str:order_id>/',views.return_order,name='return_order'),
    path('verify-payment/', views.verify_payment, name='verify-payment'),
    path('apply_coupon', views.apply_coupon,name='apply_coupon'),
    path('remove_coupon',views.remove_coupon,name='remove_coupon'),
    path('return_request/<str:order_id>/',views.return_request, name='return_request'),
    path('generate_invoice/<str:order_id>/', views.generate_invoice, name='generate_invoice'),
    path('submit_review/<str:order_id>/', views.submit_review, name='submit_review'),
]
