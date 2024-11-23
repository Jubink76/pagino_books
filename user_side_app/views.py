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
from order_detail_app.models import OrderDetails,OrderItem
from django.urls import reverse

##########################################################################################################

def shop_page(request):
    # Get filters and sorting options from the request
    search_query = request.GET.get('search', '').strip()  # Search text
    sort_option = request.GET.get('sort', 'popularity')  # Default sort
    filter_category = request.GET.get('category', '')  
    filter_author = request.GET.get('author', '')  
    price_min = request.GET.get('price_min', 0)  
    price_max = request.GET.get('price_max', 10000)  

    books = BookTable.objects.prefetch_related('images').filter(is_available=True, is_deleted=False)

    # search filter (search in book name and description)
    if search_query:
        books = books.filter(Q(book_name__icontains=search_query) | Q(description__icontains=search_query))

    #  category filter
    if filter_category:
        books = books.filter(category__name__iexact=filter_category)

    #  author filter
    if filter_author:
        books = books.filter(author__name__iexact=filter_author)

    #  price range filter
    books = books.filter(offer_price__gte=price_min, offer_price__lte=price_max)

    # Apply sorting
    
    if sort_option == 'price_low_to_high':
        books = books.order_by('offer_price')
    elif sort_option == 'price_high_to_low':
        books = books.order_by('-offer_price')
    elif sort_option == 'new_arrivals':
        books = books.order_by('-publication_date')
    elif sort_option == 'a_to_z':
        books = books.order_by('book_name')
    elif sort_option == 'z_to_a':
        books = books.order_by('-book_name')

    # Set up pagination (16 books per page)
    paginator = Paginator(books, 16)
    page_number = request.GET.get('page')
    books = paginator.get_page(page_number)

    # Render the template with the filtered, sorted, and paginated books
    return render(request, 'shop_page.html', {
        'books': books,
        'search_query': search_query,
        'sort_option': sort_option,
        'filter_category': filter_category,
        'filter_author': filter_author,
        'price_min': price_min,
        'price_max': price_max,
    })

##########################################################################################################

def single_detail(request,pk):
    book = get_object_or_404(BookTable,id=pk)
    images = book.images.all()

    # fetch related products exclude the main book
    related_books = BookTable.objects.filter(
        category = book.category,
        is_available = True,
        is_deleted = False
    ).exclude(id=pk)[:6]
    return render(request,'single_detail.html',{'book':book,'images':images,'related_books':related_books})

###########################################################################################################

def single_category(request,pk):
    category = get_object_or_404(CategoryTable,id=pk,is_available=True,is_deleted=False)
    books = BookTable.objects.prefetch_related('images').filter(category=category,is_available=True,is_deleted=False)
    # Set up pagination
    paginator = Paginator(books, 16)  # Display 16 books per page
    page_number = request.GET.get('page')
    books = paginator.get_page(page_number)
    return render(request,'single_category.html',{'books':books,'category':category})

###########################################################################################################

def cart_page(request):
    if request.user.is_authenticated:
        user_id = request.user.id
        cart_items = CartTable.objects.filter(user=request.user)
    else:
        if not request.session.session_key:
            request.session.create()
        session_id = request.session.session_key
        cart_items = CartTable.objects.filter(session_id=session_id)

    grand_total = cart_items.aggregate(total=Sum('total_price'))['total'] or 0

    return render(request,'cart_page.html',{'cart_items':cart_items,'grand_total': grand_total})

###########################################################################################################


def add_to_cart(request, book_id):
    book = get_object_or_404(BookTable, id=book_id)
    item_price = book.offer_price if book.offer_price else book.base_price

    try:
        if request.user.is_authenticated:
            cart_item, created = CartTable.objects.get_or_create(
                user=request.user,
                book=book,
                defaults={
                    'quantity': 1,
                    'item_price': item_price,
                    'total_price': item_price,
                }
            )
        else:
            session_id = request.session.session_key or request.session.create()
            cart_item, created = CartTable.objects.get_or_create(
                session_id=session_id,
                book=book,
                defaults={
                    'quantity': 1,
                    'item_price': item_price,
                    'total_price': item_price,
                }
            )

        if created:
            if book.stock_quantity > 0:
                book.stock_quantity -= 1
                if book.stock_quantity <= 0:
                    book.is_available = False
                book.save()
                return JsonResponse({
                    'status': 'success',
                    'message': f"{book.book_name} added to your cart.",
                    'redirect_url': reverse('cart_page')
                })
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': f"{book.book_name} is out of stock."
                })

        if not created:
            cart_item.quantity += 1
            cart_item.save()

        return JsonResponse({
            'status': 'success',
            'message': f"{book.book_name} added to your cart.",
            'redirect_url': reverse('cart_page')
        })

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': 'An error occurred while adding to cart.',
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
            
            max_allowed = min(10, book.stock_quantity)
            if new_quantity > max_allowed:
                error_message = 'Maximum quantity allowed is 10.' if max_allowed == 10 else f'Only {max_allowed} items available in stock.'
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
    book = get_object_or_404(BookTable, id=book_id)

    try:
        if request.user.is_authenticated:
            whishlist_item, created = WhishlistTable.objects.get_or_create(
                user=request.user,
                book=book
            )
        else:
            session_id = request.session.session_key or request.session.create()
            whishlist_item, created = WhishlistTable.objects.get_or_create(
                session_id=session_id,
                book=book,
            )

        if created:
            return JsonResponse({
                'status': 'success',
                'message': 'Book added to wishlist successfully!',
                'redirect_url': reverse('whishlist_page')  # Ensure this URL name exists
            })
        else:
            return JsonResponse({
                'status': 'info',
                'message': 'This book is already in your wishlist.',
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

    addresses = AddressTable.objects.filter(user=request.user)
    cart_items = CartTable.objects.filter(user=request.user)
    grand_total = sum(item.quantity * item.item_price for item in cart_items)
    discount = 0  # Placeholder for discount logic
    final_total = grand_total - discount
    show_new_address_form = request.GET.get('show_new_address_form', 'false') == 'true'
    context = {
        "addresses": addresses,
        "cart_items": cart_items,
        "grand_total": grand_total,
        "discount": discount,
        "final_total": final_total,
        'show_new_address_form': show_new_address_form,
    }

    return render(request,'checkout_page.html',context)

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
        address_type = request.POST.get('address_type', 'Home')  # Default to Home if not specified

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
        elif not re.match(r'^\d{10}$', address_phone):
            errors['address_phone'] = 'Phone number must be 10 digits'

        if not state:
            errors['state'] = 'State is required'
        elif not re.match(r'^[a-zA-Z\s]*$', state):
            errors['state'] = 'State should only contain letters and spaces'

        # If there are any errors, return them
        if errors:
            return JsonResponse({
                'status': 'error',
                'errors': errors
            })

        try:
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
                address_type=address_type
            )
            address.save()

            return JsonResponse({
                'status': 'success',
                'message': 'Address added successfully!'
            })

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': 'An error occurred while saving the address.'
            })

    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    })

###################################################################################################################

def order_success(request,order_id):
    return render(request,'order_success.html')


###################################################################################################################