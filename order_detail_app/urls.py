from django.urls import path
from . import views
urlpatterns = [
    path('create-order/',views.create_order,name='create-order'),
    path('cancel_order/<str:order_id>/', views.cancel_order, name='cancel_order'),
    path('user_orders/<str:order_id>/item/<int:order_item_id>/cancel/', views.user_single_item_cancel, name='user_single_item_cancel'),
    path('verify-payment/', views.verify_payment, name='verify-payment'),
]
