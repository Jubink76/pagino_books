from django.urls import path
from . import views
urlpatterns = [
    path('create-order/',views.create_order,name='create-order'),
    path('cancel_order/<str:order_id>/', views.cancel_order, name='cancel_order'),
    path('user_order_detail/<str:order_id>/item/<int:order_item_id>/cancel/', views.user_single_item_cancel, name='user_single_item_cancel'),
    #path('return_order/<str:order_id>/',views.return_order,name='return_order'),
    path('verify-payment/', views.verify_payment, name='verify-payment'),
    path('apply_coupon', views.apply_coupon,name='apply_coupon'),
    path('remove_coupon',views.remove_coupon,name='remove_coupon'),
    path('return_request/<str:order_id>/',views.return_request, name='return_request'),
    path('generate_invoice/<str:order_id>/', views.generate_invoice, name='generate_invoice'),
    path('submit_review/<str:order_id>/', views.submit_review, name='submit_review'),
    path('return-request/<int:return_request_id>/approve/',views.approve_return_request, name='approve_return_request'),
    path('return-request/<int:return_request_id>/reject/',views.reject_return_request, name='reject_return_request'),
    #path('return-item/<str:order_id>/<int:item_id>/', views.return_single_item, name='user_single_item_return'),
]
