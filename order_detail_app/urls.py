from django.urls import path
from . import views
urlpatterns = [
    path('create-order/',views.create_order,name='create-order'),
    path('cancel_order/<str:order_id>/', views.cancel_order, name='cancel_order'),
]
