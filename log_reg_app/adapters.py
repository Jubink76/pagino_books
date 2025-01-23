
from django.shortcuts import redirect
from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.db import IntegrityError
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from log_reg_app.models import UserTable
from django.contrib import messages

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        user = sociallogin.user
        email = user.email
        
        if not email:
            return  # Skip if no email is provided

        try:
            # Check if a user with the same email already exists
            existing_user = UserTable.objects.get(email=email)

            if existing_user.is_superuser:
                messages.error(request, "Superusers are not allowed to log in using Google authentication.")
                raise PermissionError("Superuser login via Google is not allowed.")
            sociallogin.connect(request, existing_user)
            
        except ObjectDoesNotExist:
            # No user exists, proceed with social login
            pass
        except MultipleObjectsReturned:
            # Handle the rare case where duplicates exist
            # Optional: Log a warning or resolve duplicates manually
            raise ValueError(f"Multiple users found with email: {email}")

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form=form)

        if sociallogin.account.provider == 'google':
            extra_data = sociallogin.account.extra_data
            user.first_name = extra_data.get('given_name', '')
            user.last_name = extra_data.get('family_name', '')

        user.save()
        return user

class CustomAccountAdapter(DefaultAccountAdapter):
    def get_login_redirect_url(self, request):
        return '/homepage_after_login/'
