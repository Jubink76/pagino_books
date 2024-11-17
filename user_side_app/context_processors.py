from adminside_app.models import CategoryTable
from adminside_app.models import BookTable
from user_side_app.models import CartTable,WhishlistTable
# Create your views here.
def list_items(request):
    categories = CategoryTable.objects.filter(is_available=True, is_deleted=False)
    books = BookTable.objects.prefetch_related('images').all() 
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
    return {'categories':categories,'books':books,'cart_items':cart_items,'whishlist_items':whishlist_items}