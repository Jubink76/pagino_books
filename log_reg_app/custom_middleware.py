from django.shortcuts import redirect
from django.urls import reverse

class AccessControlMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Public pages allowed for unauthenticated users
        public_urls = [
            reverse('user_login'),      
            reverse('user_signup'),     
            reverse('forgot_password'),
            reverse('homepage_before_login'),
            reverse('google_callback'), 
            reverse('admin_login'),
        ]
        private_user_urls = [
            reverse('homepage_after_login'),
        ]
        private_admin_urls = [
            reverse('admin_dashboard')
        
        ]

        if request.user.is_authenticated and not request.user.is_superuser and request.path in public_urls:
            return redirect('homepage_after_login')
        if request.user.is_superuser and request.path in public_urls:
            return redirect('admin_dashboard')
        
        response = self.get_response(request)
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'

        return response