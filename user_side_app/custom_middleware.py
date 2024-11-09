from django.shortcuts import redirect
from django.urls import reverse

class UserAccessControlMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # URLs specific to authenticated user actions
        user_action_urls = [
            reverse('cart_page'),
            reverse('whishlist_page')
        ]


        # Prevent admins from accessing user-specific actions
        if request.user.is_superuser and request.path in user_action_urls:
            return redirect('admin_login')

        # Proceed with the request if the checks pass
        response = self.get_response(request)
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'

        return response
