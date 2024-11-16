from django.shortcuts import render,redirect
from django.contrib import messages
from user_profile_app.models import AddressTable
from user_side_app.models import CartTable
from .models import OrderDetails, OrderItem
import random
import string
from django.db import transaction


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
            print("order created ")
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
            print("cart items deleted")
            messages.success(request, "Order placed successfully!")
            return redirect('order_success', order_id=order.order_id)

    except AddressTable.DoesNotExist:
        messages.error(request, "Selected address not found.")
        return redirect('checkout_page')
    except ValueError as e:
        messages.error(request, str(e))
        return redirect('checkout_page')
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('checkout_page')