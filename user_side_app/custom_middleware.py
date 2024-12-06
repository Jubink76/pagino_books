from django.shortcuts import redirect
from django.urls import reverse
from django.utils.timezone import now
from .models import CartTable, WhishlistTable, BookTable

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


class SessionExpiryMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Check if session exists and is active
        session_key = request.session.session_key
        if not session_key:
            return response
        
        # Get all cart and wishlist items associated with this session
        cart_items = CartTable.objects.filter(session_id=session_key)
        wishlist_items = WhishlistTable.objects.filter(session_id=session_key)

        if cart_items.exists() or wishlist_items.exists():
            # Check if the session has expired
            last_accessed_time = request.session.get('last_accessed_time', None)
            session_duration = 60 * 60 * 24 * 7  # 7 days session duration
            
            if last_accessed_time and (now() - last_accessed_time).total_seconds() > session_duration:
                # The session has expired, handle stock and cart item deletion
                for cart_item in cart_items:
                    book = cart_item.book
                    cart_item.session_is_available = False
                    cart_item.save()

                    # Update the stock based on the quantity in the cart
                    book.stock_quantity += cart_item.quantity
                    if book.stock_quantity > 0:
                        book.is_available = True
                    book.save()
                
                for wishlist_item in wishlist_items:
                    wishlist_item.session_is_available = False
                    wishlist_item.save()
                
                # Clear the session expiry time
                request.session['last_accessed_time'] = now()
        
        return response
