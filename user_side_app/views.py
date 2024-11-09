from django.shortcuts import render, redirect
from adminside_app.models import BookTable,CategoryTable
from user_side_app.models import CartTable
from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect
from django.db.models import Sum
from django.http import JsonResponse
import json


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
                book.is_available = False  # Mark as unavailable if stock reaches zero
            book.save()
            messages.success(request, f"{book.book_name} added to your cart.")
        else:
            messages.error(request, f"{book.book_name} is out of stock.")
            return redirect('cart_page')
    

    if not created:
        cart_item.quantity += 1
        cart_item.save()  # This will trigger the save method which updates total_price and grand_total

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
        book.is_available = True  # Mark as available if stock is above zero
    book.save()

    cart_item.delete()

    messages.success(request, "Item removed from the cart.")

    return redirect('cart_page')

###########################################################################################################

def update_cart_quantity(request, item_id):
    if request.method == 'POST':
        cart_item = get_object_or_404(CartTable, id=item_id)
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
            book.stock_quantity -= quantity_diff  # Adjust stock based on quantity change
            if book.stock_quantity <= 0:
                book.is_available = False  # Mark book as unavailable if stock is zero
            book.save()

            # Calculate grand total across all items in the user's cart
            cart_items = CartTable.objects.filter(user=request.user)
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
    return render(request,'whishlist_page.html')