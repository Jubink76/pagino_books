"""
URL configuration for project_book project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static
from log_reg_app import views
from django.shortcuts import redirect
from django.urls import path, include
# from log_reg_app.views import CustomGoogleCallbackView
# from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.urls import urlpatterns as social_account_urls
urlpatterns = [
    # path('accounts/google/login/callback/', 
    #      CustomGoogleCallbackView.as_view(), 
    #      name='google_callback'),
    # path('',views.homepage_before_login,name='homepage_before_login'),
    # path('homepage_after_login/', views.homepage_after_login, name='homepage_after_login'),
    #path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('accounts/', include(social_account_urls)),
    path('', include('log_reg_app.urls')),
    path('',include('adminside_app.urls')),
    path('',include('user_side_app.urls')),
    path('',include('user_profile_app.urls')),
    path('',include('order_detail_app.urls')),
    path('paypal/', include('paypal.standard.ipn.urls')),

]

urlpatterns += static(settings.STATIC_URL, document_root = settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root = settings.MEDIA_ROOT)