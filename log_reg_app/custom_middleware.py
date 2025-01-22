from django.shortcuts import redirect
from django.urls import reverse, resolve, Resolver404
from django.http import Http404, HttpResponseNotFound
from django.template.loader import render_to_string

class AccessControlMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # First check if user is authenticated and the path is valid
            try:
                resolve(request.path)
        
                if request.user.is_authenticated and not request.user.is_superuser:
                # Public pages allowed for unauthenticated users
                    public_urls = [
                        reverse('user_login'),      
                        reverse('user_signup'),     
                        reverse('forgot_password'),
                        reverse('homepage_before_login'),
                        reverse('google_callback'), 
                        reverse('admin_login'),
                    ]
                    if request.path == reverse('user_logout'):
                        return self.get_response(request)
                    
                    if request.path in public_urls:
                        return redirect('homepage_after_login')

                elif request.user.is_superuser:
                    public_urls = [
                        reverse('user_login'),      
                        reverse('user_signup'),     
                        reverse('forgot_password'),
                        reverse('homepage_before_login'),
                        reverse('google_callback'), 
                        reverse('admin_login'),
                    ]
                    if request.path == reverse('admin_logout'):
                        return self.get_response(request)
                    
                    if request.path in public_urls:
                        return redirect('admin_dashboard')
                response = self.get_response(request)
                response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
                response['Pragma'] = 'no-cache'
                return response
            
                
            except Resolver404:
                context = {
                'request': request,
                'user': request.user,  # Explicitly include user in context
            }
            
            if request.user.is_authenticated and request.user.is_superuser:
                html = render_to_string('admin_404.html', context, request=request)
            else:
                html = render_to_string('404.html', context, request=request)
            return HttpResponseNotFound(html)