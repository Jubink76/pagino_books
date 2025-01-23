from django.shortcuts import render, redirect
from adminside_app.models import BookTable,CategoryTable
from user_side_app.models import CartTable,WhishlistTable
from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect
from django.db.models import Sum
from django.http import JsonResponse
import json
from user_profile_app.models import AddressTable
from django.contrib.auth.decorators import login_required
from order_detail_app.models import OrderDetails,OrderItem, OfferTable, CouponTable,ReviewTable,CouponUsage
from django.urls import reverse
import re
from django.db.models import Q,F
from django.utils.timezone import now, localtime
from django.db.models import Avg, Count
from django.utils import timezone
##########################################################################################################

def shop_page(request):

    sort = request.GET.get('sort', 'popularity')  # Default sort
    filter_category = request.GET.get('category', '')  
    filter_author = request.GET.get('author', '')  
    price_min = request.GET.get('price_min', 0)  
    price_max = request.GET.get('price_max', 10000) 
    search_query = str(request.GET.get('search', '')).strip()
    search_query = ' '.join(word for word in search_query.split() if word) 

    books = BookTable.objects.prefetch_related('images').filter(is_deleted=False)

    active_offers = OfferTable.objects.filter(is_active=True, valid_from__lte=now(), valid_to__gte=now())

    # Apply active offers dynamically
    for book in books:
        base_price = book.base_price
        product_offer_price = None
        category_offer_price = None
        applied_offer = None

        # Check for product-specific offer
        product_offer = active_offers.filter(offer_type='product', product=book).first()
        if product_offer:
            if product_offer.discount_type == 'percentage':
                product_offer_price = base_price - (base_price * product_offer.discount_value / 100)
            elif product_offer.discount_type == 'fixed':
                product_offer_price = base_price - product_offer.discount_value

        # Check for category-specific offer
        category_offer = active_offers.filter(offer_type='category', category=book.category).first()
        if category_offer:
            if category_offer.discount_type == 'percentage':
                category_offer_price = base_price - (base_price * category_offer.discount_value / 100)
            elif category_offer.discount_type == 'fixed':
                category_offer_price = base_price - category_offer.discount_value

        # Determine the lowest price and the corresponding offer
        effective_price = base_price  # Start with the base price
        if product_offer_price is not None and product_offer_price < effective_price:
            effective_price = product_offer_price
            applied_offer = product_offer
        if category_offer_price is not None and category_offer_price < effective_price:
            effective_price = category_offer_price
            applied_offer = category_offer

        # Update the book's price and applied offer
        book.offer_price = effective_price
        book.applied_offer = applied_offer
        book.additional_offer_applied = applied_offer is not None
        book.save()

    if search_query:
        # Split the search query into words and create Q objects for each word
        search_words = search_query.split()
        search_filter = Q()
        
        for word in search_words:
            # Create a Q object for each search term
            word_filter = (
                Q(book_name__icontains=word) |
                Q(author__name__icontains=word) |
                Q(language__name__icontains=word) |
                Q(description__icontains=word)
            )
            # Combine with AND operation
            search_filter &= word_filter
        
        books = books.filter(search_filter).distinct()


    if filter_category:
        books = books.filter(category__name__iexact=filter_category)

    if filter_author:
        books = books.filter(author__name__iexact=filter_author)

    books = books.filter(offer_price__gte=price_min, offer_price__lte=price_max)

    # Apply sorting
    if sort == 'price_low':
        books = books.order_by('offer_price')
    elif sort == 'price_high':
        books = books.order_by('-offer_price')
    elif sort == 'name_asc':
        books = books.order_by('book_name')
    elif sort == 'name_desc':
        books = books.order_by('-book_name')
    elif sort == 'new_arrivals':
        books = books.order_by('-publication_date')  
    else:
        books = books.order_by('id')

    # Set up pagination (16 books per page)
    paginator = Paginator(books, 16)
    page_number = request.GET.get('page')
    books = paginator.get_page(page_number)

    # Render the template with the filtered, sorted, and paginated books
    return render(request, 'shop_page.html', {
        'books': books,
        'sort_option': sort,
        'filter_category': filter_category,
        'filter_author': filter_author,
        'price_min': price_min,
        'price_max': price_max,
        'search_query': search_query,
    })


##########################################################################################################

def single_detail(request,pk):


    book = get_object_or_404(BookTable,id=pk)

    images = book.images.all()

    rating_data = ReviewTable.objects.filter(book=book).aggregate(
    average_rating=Avg('rating'),
    review_count=Count('id')
    )

    average_rating = rating_data['average_rating'] or 0  # Default to 0 if no reviews
    review_count = rating_data['review_count'] or 0  

    current_time = now()
    local_current_time = localtime(current_time)
    active_offers = OfferTable.objects.filter(is_active=True, valid_from__lte=now(), valid_to__gte=now())
    # Calculate the offer price for the main book
    base_price = book.base_price
    product_offer_price = None
    category_offer_price = None
    applied_offer = None

    # Check for product-specific offer
    product_offer = active_offers.filter(offer_type='product', product=book).first()

    if product_offer:
        if product_offer.discount_type == 'percentage':
            product_offer_price = base_price - (base_price * product_offer.discount_value / 100)
        elif product_offer.discount_type == 'fixed':
            product_offer_price = base_price - product_offer.discount_value

    # Check for category-specific offer
    category_offer = active_offers.filter(offer_type='category', category=book.category).first()
    
    if category_offer:
        if category_offer.discount_type == 'percentage':
            category_offer_price = base_price - (base_price * category_offer.discount_value / 100)
        elif category_offer.discount_type == 'fixed':
            category_offer_price = base_price - category_offer.discount_value

    # Determine the lowest price and the corresponding offer
    effective_price = base_price  # Start with the base price
    if product_offer_price is not None and product_offer_price < effective_price:
        effective_price = product_offer_price
        applied_offer = product_offer
    if category_offer_price is not None and category_offer_price < effective_price:
        effective_price = category_offer_price
        applied_offer = category_offer

    # Update the book's offer price and applied offer
    book.offer_price = round(effective_price,2)
    book.applied_offer = applied_offer
    book.additional_offer_applied = applied_offer is not None
    book.save()
    
    # fetch related products exclude the main book
    related_books = BookTable.objects.filter(
        category = book.category,
        is_available = True,
        is_deleted = False
    ).exclude(id=pk)[:6]

    related_books_data = []
    for related_book in related_books:
        related_rating_data = ReviewTable.objects.filter(book=related_book).aggregate(
            average_rating=Avg('rating'),
            review_count=Count('id')
        )
        related_books_data.append({
            'book': related_book,
            'average_rating': related_rating_data['average_rating'] or 0,
            'review_count': related_rating_data['review_count'] or 0,
        })
    return render(request,'single_detail.html',{'book':book,
                                                'images':images,
                                                'related_books':related_books_data,
                                                'average_rating': average_rating,
                                                'review_count': review_count,
                                                'rating_range': range(1, 6),})

###########################################################################################################

def single_category(request,pk):
    
    # Get filters and sorting options from the request
    search_query = request.GET.get('search', '').strip()  # Search text
    sort = request.GET.get('sort', 'popularity')  # Default sort
    filter_category = request.GET.get('category', '')  
    filter_author = request.GET.get('author', '')  
    price_min = request.GET.get('price_min', 0)  
    price_max = request.GET.get('price_max', 10000)

    category = get_object_or_404(CategoryTable,id=pk,is_available=True,is_deleted=False)
    books = BookTable.objects.prefetch_related('images').filter(category=category,is_deleted=False)

    active_offers = OfferTable.objects.filter(is_active=True, valid_from__lte=now(), valid_to__gte=now())

    # Apply active offers dynamically
    for book in books:
        base_price = book.base_price
        product_offer_price = None
        category_offer_price = None
        applied_offer = None

        # Check for product-specific offer
        product_offer = active_offers.filter(offer_type='product', product=book).first()
        if product_offer:
            if product_offer.discount_type == 'percentage':
                product_offer_price = base_price - (base_price * product_offer.discount_value / 100)
            elif product_offer.discount_type == 'fixed':
                product_offer_price = base_price - product_offer.discount_value

        # Check for category-specific offer
        category_offer = active_offers.filter(offer_type='category', category=book.category).first()
        if category_offer:
            if category_offer.discount_type == 'percentage':
                category_offer_price = base_price - (base_price * category_offer.discount_value / 100)
            elif category_offer.discount_type == 'fixed':
                category_offer_price = base_price - category_offer.discount_value

        # Determine the lowest price and the corresponding offer
        effective_price = base_price  # Start with the base price
        if product_offer_price is not None and product_offer_price < effective_price:
            effective_price = product_offer_price
            applied_offer = product_offer
        if category_offer_price is not None and category_offer_price < effective_price:
            effective_price = category_offer_price
            applied_offer = category_offer

        # Update the book's price and applied offer
        book.offer_price = effective_price
        book.applied_offer = applied_offer
        book.additional_offer_applied = applied_offer is not None
        book.save()

    if search_query:
        books = books.filter(Q(book_name__icontains=search_query) | Q(description__icontains=search_query))

    if filter_category:
        books = books.filter(category__name__iexact=filter_category)

    if filter_author:
        books = books.filter(author__name__iexact=filter_author)

    books = books.filter(offer_price__gte=price_min, offer_price__lte=price_max)

    # Apply sorting
    
    if sort == 'price_low':
        books = books.order_by('offer_price')
    elif sort == 'price_high':
        books = books.order_by('-offer_price')
    elif sort == 'name_asc':
        books = books.order_by('book_name')
    elif sort == 'name_desc':
        books = books.order_by('-book_name')
    elif sort == 'new_arrivals':
        books = books.order_by('-publication_date')  
    else:
        books = books.order_by('id')

    # Set up pagination
    paginator = Paginator(books, 16)  # Display 16 books per page
    page_number = request.GET.get('page')
    books = paginator.get_page(page_number)

    return render(request,'single_category.html',{
        'books':books,
        'search_query': search_query,
        'sort': sort,
        'filter_category': filter_category,
        'filter_author': filter_author,
        'price_min': price_min,
        'price_max': price_max})                                 

###########################################################################################################

def cart_page(request):

    if request.user.is_authenticated:
        user_id = request.user.id
        cart_items = CartTable.objects.filter(user=request.user, session_is_available=True)
    else:
        if not request.session.session_key:
            request.session.create()
        session_id = request.session.session_key
        cart_items = CartTable.objects.filter(session_id=session_id, session_is_available=True)

    grand_total = cart_items.aggregate(total=Sum('total_price'))['total'] or 0

    if not request.user.is_authenticated:
        cart_items_expired = CartTable.objects.filter(session_id=session_id, session_is_available=False)
        
        for cart_item in cart_items_expired:
            book = cart_item.book
            book.stock_quantity += cart_item.quantity
            if book.stock_quantity > 0:
                book.is_available = True
            else:
                book.is_available = False
            book.save()

            cart_item.delete()  

    return render(request, 'cart_page.html', {
        'cart_items': cart_items,
        'grand_total': grand_total
    })

###########################################################################################################

def add_to_cart(request, book_id):
    if not request.user.is_authenticated:
        return JsonResponse({
            'status': 'login_required',
            'message': 'Please login to add items to your cart', 
            'redirect_url': reverse('user_login')
        })
    
    book = get_object_or_404(BookTable, id=book_id)
    item_price = book.offer_price if book.offer_price else book.base_price

    try:
        cart_item = CartTable.objects.filter(user=request.user, book=book).first()
        
        if cart_item:

            if cart_item.quantity >=1:
                return JsonResponse({
                    'status': 'info',
                    'message': f"Already'{book.book_name}'in your cart.",
                })

            cart_item.quantity += 1
            cart_item.total_price = cart_item.item_price * cart_item.quantity
            cart_item.save()
            return JsonResponse({
                'status': 'success',
                'message': f"Added another copy of '{book.book_name}' to your cart.",
                'redirect_url': reverse('cart_page')
            })
        else:
            if book.stock_quantity > 0:
                cart_item = CartTable.objects.create(
                    user=request.user,
                    book=book,
                    quantity=1,
                    item_price=item_price,
                    total_price=item_price,
                )

                book.stock_quantity -= 1
                if book.stock_quantity <= 0:
                    book.is_available = False
                book.save()
                
                return JsonResponse({
                    'status': 'success',
                    'message': f"'{book.book_name}' has been added to your cart.",
                    'redirect_url': reverse('cart_page')
                })
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': f"Sorry, '{book.book_name}' is currently out of stock."
                })

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': 'An error occurred while processing your request. Please try again.',
        })

###########################################################################################################
def delete_cart_item(request, item_id):
    try:
        if request.user.is_authenticated:
            cart_item = get_object_or_404(CartTable, id=item_id, user=request.user)
        else:
            session_id = request.session.session_key
            cart_item = get_object_or_404(CartTable, id=item_id, session_id=session_id)

        # Update stock and delete cart item
        book = cart_item.book
        book.stock_quantity += cart_item.quantity
        if book.stock_quantity > 0:
            book.is_available = True  
        book.save()

        cart_item.delete()

        return JsonResponse({'status': 'success', 'message': 'Item removed from the cart.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': 'Failed to remove item from the cart.'})

###########################################################################################################

def update_cart_quantity(request, item_id):
    if request.method == 'POST':
        if request.user.is_authenticated:
            cart_item = get_object_or_404(CartTable, id=item_id, user=request.user)
        else:
            if not request.session.session_key:
                request.session.create()
            session_key = request.session.session_key
            cart_item = get_object_or_404(CartTable, id=item_id, session_id=session_key)

        book = cart_item.book

        try:
            data = json.loads(request.body)
            new_quantity = int(data.get('quantity', 0))
            
            # Validate quantity
            if new_quantity < 1:
                return JsonResponse({
                    'error': 'Quantity cannot be zero or less.',
                    'current_quantity': cart_item.quantity,
                    'item_total': float(cart_item.total_price),
                }, status=400)
            
            max_allowed = min(5, book.stock_quantity)
            if new_quantity > max_allowed:
                error_message = 'Maximum quantity allowed is 5.' if max_allowed == 5 else f'Only {max_allowed} items available in stock.'
                return JsonResponse({
                    'error': error_message,
                    'current_quantity': cart_item.quantity,
                    'item_total': float(cart_item.total_price),
                }, status=400)

            # Update cart item and book stock
            quantity_diff = new_quantity - cart_item.quantity
            cart_item.quantity = new_quantity
            cart_item.total_price = cart_item.item_price * new_quantity
            cart_item.save()

            book.stock_quantity -= quantity_diff
            if book.stock_quantity <= 0:
                book.is_available = False
            book.save()

            # Calculate grand total
            if request.user.is_authenticated:
                cart_items = CartTable.objects.filter(user=request.user)
            else:
                cart_items = CartTable.objects.filter(session_id=session_key)

            grand_total = sum(item.total_price for item in cart_items)

            return JsonResponse({
                'success': True,
                'item_total': float(cart_item.total_price),
                'grand_total': float(grand_total),
                'current_quantity': cart_item.quantity,
                'max_quantity': max_allowed,
            })

        except (ValueError, TypeError, json.JSONDecodeError):
            return JsonResponse({
                'error': 'Invalid data format.',
                'current_quantity': cart_item.quantity,
                'item_total': float(cart_item.total_price),
            }, status=400)

    return JsonResponse({'error': 'Invalid request method'}, status=400)

###########################################################################################################

def whishlist_page(request):
    if request.user.is_authenticated:
        user_id = request.user.id 
        whishlist_items = WhishlistTable.objects.filter(user = request.user)
    else:
        if not request.session.session_key:
            request.session.create()
        session_id = request.session.session_key
        whishlist_items = WhishlistTable.objects.filter(session_id= session_id)

    return render(request,'whishlist_page.html',{'whishlist_items':whishlist_items})

###########################################################################################################

def add_to_whishlist(request, book_id):
    # Require authentication
    if not request.user.is_authenticated:
        return JsonResponse({
            'status': 'login_required',
            'message': 'Please login to add items to your wishlist',
            'redirect_url': reverse('user_login')
        })
    
    book = get_object_or_404(BookTable, id=book_id)
    
    try:
        whishlist_item = WhishlistTable.objects.filter(
            user=request.user,
            book=book
        ).first()
        
        if whishlist_item:
            return JsonResponse({
                'status': 'info',
                'message': f"'{book.book_name}' is already in your wishlist.",
                'redirect_url': reverse('whishlist_page')
            })
        
        # Add new item to wishlist
        whishlist_item = WhishlistTable.objects.create(
            user=request.user,
            book=book
        )
    
        return JsonResponse({
            'status': 'success',
            'message': f"'{book.book_name}' has been added to your wishlist.",
            'redirect_url': reverse('whishlist_page')
        })

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': 'An error occurred while adding to the wishlist.'
        })
#################################################################################################################

def del_whishlist_item(request,book_id):
    try:
        if request.user.is_authenticated:
            whishlist_item = get_object_or_404(WhishlistTable, book_id=book_id, user=request.user)
        else:
            session_id = request.session.session_key
            whishlist_item = get_object_or_404(WhishlistTable,  book_id=book_id, session_id=session_id)
        whishlist_item.delete()
        return JsonResponse({'status': 'success', 'message': 'Item removed from wishlist.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': 'Failed to remove item from wishlist.'})

###################################################################################################################
@login_required
def checkout_page(request):
    user = request.user
    current_time = timezone.now()
    
    # Fetch active coupons within valid date range
    available_coupons = CouponTable.objects.filter(
        is_active=True,
        valid_from__lte=current_time,
        valid_to__gte=current_time
    )
    print(f"thi is first available coupon,{available_coupons}")
    # Get user's used coupons
    used_coupon_ids = CouponUsage.objects.filter(
        user=user,
        is_used=True
    ).values_list('coupon_id', flat=True)
    
    # Filter available coupons based on usage limits
    available_coupons = available_coupons.exclude(
        id__in=used_coupon_ids
    ).annotate(
        total_uses=Count('couponusage'),
        user_uses=Count(
            'couponusage',
            filter=Q(couponusage__user=user)
        )
    ).filter(
        Q(max_uses__isnull=True) | Q(total_uses__lt=F('max_uses')),
        user_uses__lt=F('max_uses_per_user')
    )
    print(f"thi is seconnd available coupon,{available_coupons}")
    # Fetch addresses and cart items
    addresses = AddressTable.objects.filter(user=user)
    cart_items = CartTable.objects.filter(user=user)
    
    # Calculate totals
    grand_total = sum(item.quantity * item.item_price for item in cart_items)
    discount = 0  # Placeholder for discount logic
    final_total = grand_total - discount
    
    # Get show_new_address_form parameter
    show_new_address_form = request.GET.get('show_new_address_form', 'false') == 'true'

    context = {
        "addresses": addresses,
        "cart_items": cart_items,
        "grand_total": grand_total,
        "discount": discount,
        "final_total": final_total,
        'show_new_address_form': show_new_address_form,
        'available_coupons': available_coupons
    }

    return render(request, 'checkout_page.html', context)

###################################################################################################################
@login_required
def checkout_add_address(request):
    if request.method == "POST":
        # Get form data
        address_name = request.POST.get('address_name', '').strip()
        street_name = request.POST.get('street_name', '').strip()
        building_no = request.POST.get('building_no', '').strip()
        landmark = request.POST.get('landmark', '').strip()
        city = request.POST.get('city', '').strip()
        pincode = request.POST.get('pincode', '').strip()
        address_phone = request.POST.get('address_phone', '').strip()
        state = request.POST.get('state', '').strip()
        address_type = request.POST.get('address_type', 'home')  # Changed default to lowercase

        # Initialize errors dictionary
        errors = {}

        # Validate each field
        if not address_name:
            errors['address_name'] = 'Full name is required'
        elif not re.match(r'^[a-zA-Z\s]*$', address_name):
            errors['address_name'] = 'Name should only contain letters and spaces'

        if not street_name:
            errors['street_name'] = 'Street address is required'

        if not building_no:
            errors['building_no'] = 'Building/Apartment number is required'

        if not city:
            errors['city'] = 'City is required'
        elif not re.match(r'^[a-zA-Z\s]*$', city):
            errors['city'] = 'City should only contain letters and spaces'

        if not pincode:
            errors['pincode'] = 'Pincode is required'
        elif not re.match(r'^\d{6}$', pincode):
            errors['pincode'] = 'Pincode must be 6 digits'

        if not address_phone:
            errors['address_phone'] = 'Phone number is required'
        elif not re.match(r'^[6-9]\d{9}$', address_phone):  # Updated to match client-side validation
            errors['address_phone'] = 'Please enter a valid 10-digit Indian phone number'

        if not state:
            errors['state'] = 'State is required'
        elif not re.match(r'^[a-zA-Z\s]*$', state):
            errors['state'] = 'State should only contain letters and spaces'

        if errors:
            return JsonResponse({
                'status': 'error',
                'message': 'Please correct the errors below.',
                'errors': errors
            }, status=400)  # Added status code

        try:
            # Check if user is authenticated
            if not request.user.is_authenticated:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Please log in to add an address.'
                }, status=403)

            # Create and save the address
            address = AddressTable(
                user=request.user,
                address_name=address_name,
                street_name=street_name,
                building_no=building_no,
                landmark=landmark,
                city=city,
                pincode=pincode,
                address_phone=address_phone,
                state=state,
                address_type=address_type.lower()  # Ensure lowercase storage
            )
            address.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Address added successfully!',
                'redirect_url': reverse('checkout_page')
            })

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': 'An error occurred while saving the address.'
            }, status=500)

    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    }, status=405)

###################################################################################################################

def order_success(request,order_id):
    return render(request,'order_success.html')


###################################################################################################################