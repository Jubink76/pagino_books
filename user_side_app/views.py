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

##########################################################################################################

def shop_page(request):
    books = BookTable.objects.prefetch_related('images').all()

    # Set up pagination
    paginator = Paginator(books, 16)  # Display 16 books per page
    page_number = request.GET.get('page')
    books = paginator.get_page(page_number)
    return render(request,'shop_page.html',{'books':books})

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
            messages.success(request, f"{book.book_name} added to your cart.")
        else:
            messages.error(request, f"{book.book_name} is out of stock.")
            return redirect('cart_page')
    

    if not created:
        cart_item.quantity += 1
        cart_item.save()  

    messages.success(request, f"{book.book_name} added to your cart.")
    return redirect('cart_page')



###########################################################################################################

def delete_cart_item(request,item_id):
    if request.user.is_authenticated:
        cart_item = get_object_or_404(CartTable, id=item_id, user=request.user)
    else:
        session_id = request.session.session_key
        cart_item = get_object_or_404(CartTable, id=item_id, session_id=session_id)

    book = cart_item.book
    book.stock_quantity += cart_item.quantity
    if book.stock_quantity > 0:
        book.is_available = True  
    book.save()

    cart_item.delete()

    messages.success(request, "Item removed from the cart.")

    return redirect('cart_page')

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
            new_quantity = data.get('quantity')
            if new_quantity < 1:
                return JsonResponse({'error': 'Quantity cannot be zero or less.'}, status=400)
            
            # Calculate the change in quantity
            quantity_diff = new_quantity - cart_item.quantity
            
            # Check if stock is sufficient for the new quantity
            if quantity_diff > 0 and new_quantity > book.stock_quantity + cart_item.quantity:
                return JsonResponse({'error': 'Not enough stock available.'}, status=400)

            # Calculate new total price and update cart item
            cart_item.quantity = new_quantity
            cart_item.total_price = cart_item.item_price * new_quantity
            cart_item.save()

            # Update available stock in BookTable
            book.stock_quantity -= quantity_diff  
            if book.stock_quantity <= 0:
                book.is_available = False  
            book.save()

            # Calculate grand total across all items in the user's cart
            if request.user.is_authenticated:
                cart_items = CartTable.objects.filter(user=request.user)
            else:
                cart_items = CartTable.objects.filter(session_id=session_key)
                
            grand_total = sum(item.total_price for item in cart_items)

            return JsonResponse({
                'item_total': cart_item.total_price,
                'grand_total': grand_total,
            })
        except ValueError:
            return JsonResponse({'error': 'Invalid quantity value.'}, status=400)
    return JsonResponse({'error': 'Invalid request'}, status=400)

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

def add_to_whishlist(request,book_id):
    book = get_object_or_404(BookTable, id=book_id)

    if request.user.is_authenticated:
        whishlist_item, created = WhishlistTable.objects.get_or_create(
            user = request.user,
            book = book
        )

    else:
        session_id = request.session.session_key or request.session.create()
        whishlist_item, created = WhishlistTable.objects.get_or_create(
            session_id=session_id,
            book=book,
        )

    if created:
        response = {'message': 'Book added to wishlist successfully!'}
        messages.success(request, response['message'])
    else:
        response = {'message': 'This book is already in your wishlist.'}
        messages.info(request, response['message'])

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse(response)

    return redirect('whishlist_page')

#################################################################################################################

def del_whishlist_item(request,book_id):
    if request.user.is_authenticated:
        whishlist_item = get_object_or_404(WhishlistTable, book_id=book_id, user=request.user)
    else:
        session_id = request.session.session_key
        whishlist_item = get_object_or_404(WhishlistTable,  book_id=book_id, session_id=session_id)

    whishlist_item.delete()
    messages.success(request,"item removed from whishlist")

    return redirect('whishlist_page')

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
        address_name = request.POST.get('address_name')
        street_name= request.POST.get('street_name')
        building_no = request.POST.get('building_no')
        landmark = request.POST.get('landmark')
        city = request.POST.get('city')
        pincode = request.POST.get('pincode')
        address_phone = request.POST.get('address_phone')
        state = request.POST.get('state')


        address = AddressTable(
                    user=request.user,
                    address_name=address_name,
                    street_name=street_name,
                    building_no=building_no,
                    landmark=landmark,
                    city=city,
                    pincode=pincode,
                    address_phone=address_phone,
                    state=state
                )

                # Attempt to save the address
        address.save()
        print("address saved")
        messages.success(request, "Address added successfully!")

    return render(request, 'checkout_page.html')
###################################################################################################################

def order_success(request,order_id):
    return render(request,'order_success.html')


###################################################################################################################