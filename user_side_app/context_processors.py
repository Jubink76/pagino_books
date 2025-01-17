from adminside_app.models import CategoryTable, BookTable
from user_side_app.models import CartTable, WhishlistTable
from order_detail_app.models import OfferTable
from django.db.models import Sum, Prefetch, Q
from django.utils.timezone import now
from django.core.cache import cache
from datetime import datetime, timedelta
import random

def list_items(request):
    """
    Context processor for common data needed across the application.
    """
    current_time = now()
    
    # Ensure session exists
    if not request.session.session_key:
        request.session.create()
    session_id = request.session.session_key

    # Get search query
    # search_query = request.GET.get('search', '')
    # print("Search query:", search_query)

    # Get categories
    categories = CategoryTable.objects.filter(
        is_available=True,
        is_deleted=False
    )

    # Get active offers
    active_offers = OfferTable.objects.filter(
        is_active=True,
        valid_to__gte=current_time
    ).select_related('category')

    # Optimize book query with all necessary relations
    books = BookTable.objects.select_related(
        'category',
        'author',
        'language',
        'applied_offer'
    ).prefetch_related(
        'images'
    ).filter(
        is_deleted=False
    )

    # # Apply search filter if search query exists
    # if search_query:
    #     books = books.filter(
    #         Q(book_name__icontains=search_query)
    #     ).distinct() 

    # Get cart and wishlist items based on authentication
    if request.user.is_authenticated:
        cart_items = CartTable.objects.filter(
            user=request.user
        ).select_related('book')
        whishlist_items = WhishlistTable.objects.filter(
            user=request.user
        ).select_related('book')
    else:
        cart_items = CartTable.objects.filter(
            session_id=session_id
        ).select_related('book')
        whishlist_items = WhishlistTable.objects.filter(
            session_id=session_id
        ).select_related('book')

    # Calculate grand total using aggregation
    grand_total = cart_items.aggregate(
        total=Sum('total_price')
    )['total'] or 0

    # Get featured product efficiently
    available_products = list(books.filter(is_available=True))
    current_product = random.choice(available_products) if available_products else None

    # Set timer for promotional countdown
    timer_end_time = (datetime.now() + timedelta(hours=24)).isoformat()

    context = {
        'categories': categories,
        'books': books,
        'active_offers': active_offers,
        'cart_items': cart_items,
        'whishlist_items': whishlist_items,
        'grand_total': grand_total,
        'product': current_product,
        'timer_end_time': timer_end_time,
        # 'search_query': search_query,
    }
    
    return context