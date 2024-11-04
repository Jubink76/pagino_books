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
        ]

        # Redirect logged-in users away from login and signup pages
        if request.user.is_authenticated and request.path in [url for url in public_urls]:
            return redirect('homepage_after_login')

        # Redirect unauthenticated users trying to access private pages
        private_urls = [
            reverse('homepage_after_login'),
        ]
        if not request.user.is_authenticated and request.path in [url for url in private_urls]:
            return redirect('user_login')

        return self.get_response(request)