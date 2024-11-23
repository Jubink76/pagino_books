from django.shortcuts import render,redirect,get_object_or_404
from django.contrib import messages
from user_profile_app.models import AddressTable
from user_side_app.models import CartTable
from .models import OrderDetails, OrderItem
import random
import string
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.http import JsonResponse
# generating unique order id
def generate_order_id():
    return ''.join(random.choices(string.ascii_uppercase + string.ascii_lowercase + string.digits, k=10))

def create_order(request):
    if request.method != "POST":
        return redirect('checkout_page')
    
    address_id = request.POST.get("savedAddress")
    payment_method = request.POST.get("payment")

    if not address_id:
        messages.error(request, "Please select a delivery address.")
        return redirect('checkout_page')
    
    if not payment_method:
        messages.error(request, "Please select a payment method.")
        return redirect('checkout_page')
    
    # Validate payment method
    valid_payment_methods = ['COD', 'ONLINE', 'WALLET']
    if payment_method not in valid_payment_methods:
        messages.error(request, "Invalid payment method selected.")
        return redirect('checkout_page')
    
    try:
        with transaction.atomic():
            address = AddressTable.objects.get(id=address_id)
            cart_items = CartTable.objects.filter(user=request.user)

            if not cart_items.exists():
                messages.error(request, "Your cart is empty.")
                return redirect('checkout_page')

            # Generate single order ID
            single_order_id = generate_order_id()

            # Calculate total amount
            grand_total = sum(
                item.quantity * item.book.offer_price 
                for item in cart_items
            )

            # Create main order
            order = OrderDetails.objects.create(
                order_id=single_order_id,
                user=request.user,
                address=address,
                payment_method=payment_method,
                total_amount=grand_total,
                order_status='Pending'
            )
            # Create order items
            for cart_item in cart_items:
                if cart_item.book.stock_quantity < cart_item.quantity:
                    raise ValueError(f"Insufficient stock for {cart_item.book.title}")
                
                OrderItem.objects.create(
                    order=order,
                    book=cart_item.book,
                    quantity=cart_item.quantity,
                    price_per_item=cart_item.book.offer_price,
                    total_price=cart_item.quantity * cart_item.book.offer_price
                )
                
                # Update stock
                cart_item.book.stock_quantity -= cart_item.quantity
                cart_item.book.save()

            # Clear cart
            cart_items.delete()
            return JsonResponse({
                'status': 'success',
                'message': 'Order placed successfully!',
                'redirect_url': reverse('order_success', kwargs={'order_id': order.order_id})
            })

    except AddressTable.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Selected address not found.'})
    except ValueError as e:
        return JsonResponse({'status': 'error', 'message': str(e)})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f"An error occurred: {str(e)}"})
    
#################################################################################################################################
@login_required
def cancel_order(request,order_id):
    if request.method == "POST":
        order = get_object_or_404(OrderDetails, order_id=order_id, user=request.user)

        if order.order_status != 'Canceled':
            order.order_status = 'Canceled'
            order.is_canceled = True
            order.save()
            return JsonResponse({
            'status': 'success',
            'message': f"Order {order.order_id} has been canceled.",
            'redirect_url': reverse('user_orders')
            })
        else:
            return JsonResponse({
            'status': 'info',
            'message': f"Order {order.order_id} is already canceled."
            })
    return redirect('user_orders')

################################################################################################################################