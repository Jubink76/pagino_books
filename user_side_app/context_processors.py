from adminside_app.models import CategoryTable
from adminside_app.models import BookTable
from user_side_app.models import CartTable,WhishlistTable
from order_detail_app.models import OfferTable
import random
from datetime import datetime, timedelta
from django.shortcuts import render
from django.utils.timezone import now
# Create your views here.
def list_items(request):
    categories = CategoryTable.objects.filter(is_available=True, is_deleted=False)
    books = BookTable.objects.prefetch_related('images').all() 
    #active_offers = OfferTable.objects.filter(is_active=True, valid_from__lte=now(), valid_to__gte=now())
    if not request.session.session_key:
        request.session.create()
    
    session_id = request.session.session_key

    if request.user.is_authenticated:
        # Fetch cart items for the logged-in user
        cart_items = CartTable.objects.filter(user=request.user)
        whishlist_items = WhishlistTable.objects.filter(user=request.user)
    else:
        # Fetch cart items for the current session
        cart_items = CartTable.objects.filter(session_id=session_id)
        whishlist_items = WhishlistTable.objects.filter(session_id = session_id)
    grand_total = sum(item.total_price for item in cart_items)

    products = list(BookTable.objects.filter(is_available=True).prefetch_related('images'))
    if products:
        current_product = random.choice(products)
    else:
        current_product = None 

    return {'categories':categories,
            'books':books,
            #'active_offers':active_offers,
            'cart_items':cart_items,
            'whishlist_items':whishlist_items,
            'grand_total':grand_total,
            'product':current_product,
            'timer_end_time': (datetime.now() + timedelta(hours=24)).isoformat(),}