# from django.shortcuts import redirect
# from django.urls import reverse

# class AdminControlMiddleware:
#     def __init__(self, get_response):
#         self.get_response = get_response

#     def __call__(self, request):
#         # Public pages allowed for unauthenticated users
#         public_urls = [
#             reverse('admin_login'),
#         ]

#         # Redirect logged-in users away from login and signup pages
#         if request.user.is_superuser and request.path in public_urls:
#             return redirect('admin_dashboard')
#         # Redirect unauthenticated users trying to access private pages
#         private_urls = [
#             reverse('admin_dashboard'),
#         ]
#         if not request.user.is_superuser and request.path in private_urls:
#             return redirect('admin_login')

#         return self.get_response(request)