from django.urls import path
from . import views

urlpatterns = [
    path('',views.homepage_before_login,name='homepage_before_login'),
    path('user_signup/',views.user_signup, name='user_signup'),
    path('user_login/',views.user_login, name='user_login'),
    path('homepage_after_login/',views.homepage_after_login, name='homepage_after_login'),
    path('user_logout/',views.user_logout, name='user_logout'),
    path('forgot_password/',views.forgot_password, name='forgot_password'),
    path('set_password/',views.set_password, name='set_password'),
    path('verify_otp/',views.verify_otp, name='verify_otp'),
    path('resend_otp/',views.resend_otp, name="resend_otp"),
    path('admin_login/',views.admin_login,name='admin_login'),
    path('admin_logout/',views.admin_logout, name='admin_logout'),
]
