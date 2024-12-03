from django.shortcuts import render,redirect,get_object_or_404
from django.contrib import messages
from user_profile_app.models import AddressTable,WalletTable
from user_side_app.models import CartTable
from .models import OrderDetails, OrderItem
import random
import string
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.http import JsonResponse
import json
import razorpay
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.timezone import now
from django.utils import timezone
from decimal import Decimal

# Initialize Razorpay client
razorpay_client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)

def generate_order_id():
    return ''.join(random.choices(string.ascii_uppercase + string.ascii_lowercase + string.digits, k=10))

def create_order(request):
    if request.method != "POST":
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'})
    
    try:
        address_id = request.POST.get("savedAddress")
        payment_method = request.POST.get("payment")
        
        if not address_id:
            return JsonResponse({'status': 'error', 'message': 'Please select a delivery address'})
            
        if not payment_method:
            return JsonResponse({'status': 'error', 'message': 'Please select a payment method'})
        
        # Validate payment method
        valid_payment_methods = ['COD', 'ONLINE', 'WALLET']
        if payment_method not in valid_payment_methods:
            return JsonResponse({'status': 'error', 'message': 'Invalid payment method selected.'})
            
        try:
            with transaction.atomic():
                address = AddressTable.objects.get(id=address_id)
                cart_items = CartTable.objects.filter(user=request.user)
                
                if not cart_items.exists():
                    return JsonResponse({'status': 'error', 'message': 'Your cart is empty.'})
                
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
                        raise ValueError(f"Insufficient stock for {cart_item.book.book_name}")
                    
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

                # Handle different payment methods
                if payment_method == 'ONLINE':
                    try:
                        # Create Razorpay order
                        razorpay_order = razorpay_client.order.create({
                            'amount': int(float(grand_total) * 100),  # Convert to paise
                            'currency': 'INR',
                            'payment_capture': '1'
                        })
                        
                        # Update order with Razorpay order ID
                        order.razorpay_order_id = razorpay_order['id']
                        order.save()
                        
                        # Don't clear cart yet for online payment
                        return JsonResponse({
                            'status': 'success',
                            'payment_method': 'ONLINE',
                            'razorpay_key': settings.RAZORPAY_KEY_ID,
                            'razorpay_order_id': razorpay_order['id'],
                            'amount': int(float(grand_total) * 100),
                            'currency': 'INR',
                            'order_id': order.order_id,
                            'customer_name': request.user.username,
                            'email': request.user.email,
                            'phone': request.user.phone if hasattr(request.user, 'phone') else ''
                        })
                    except Exception as e:
                        # If Razorpay order creation fails, delete the order and raise error
                        order.delete()
                        raise ValueError(f"Failed to create payment: {str(e)}")
                else:
                    # For COD and WALLET payments
                    # Clear cart immediately
                    cart_items.delete()
                    
                    redirect_url = request.build_absolute_uri(
                        reverse('order_success', kwargs={'order_id': order.order_id})
                    )
                    return JsonResponse({
                        'status': 'success',
                        'payment_method': payment_method,
                        'message': 'Order placed successfully!',
                        'redirect_url': redirect_url
                    })
                    
        except AddressTable.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Selected address not found.'})
        except ValueError as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f"An error occurred: {str(e)}"})
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': 'An unexpected error occurred while processing your order'
        })
#################################################################################################################################
@login_required
def cancel_order(request, order_id):
    if request.method == "POST":
        order = get_object_or_404(OrderDetails, order_id=order_id, user=request.user)

        # Check if the order is already canceled
        if order.order_status != 'Canceled':
            # Set order status to canceled
            order.order_status = 'Canceled'
            order.is_canceled = True
            order.save()

            # Refund to wallet if the payment method is ONLINE
            if order.payment_method == 'ONLINE':
                # Get the user's current wallet balance
                wallet, created = WalletTable.objects.get_or_create(user=request.user)

                
                # Create a new transaction entry for the refund
                new_wallet_entry = WalletTable(
                    user=request.user,
                    available_balance=wallet.available_balance + order.total_amount,  # Add the refunded amount to the existing balance
                    transaction_type='refund',
                    transaction_amount=order.total_amount,
                    description=f"Refund for canceled order {order.order_id}",
                    transaction_time=timezone.now()
                )
                new_wallet_entry.save()  # Save the new record

                return JsonResponse({
                    'status': 'success',
                    'message': f"Order {order.order_id} has been canceled and refunded.",
                    'redirect_url': reverse('user_orders')
                })
            else:
                return JsonResponse({
                    'status': 'success',
                    'message': f"Order {order.order_id} has been canceled (COD).",
                    'redirect_url': reverse('user_orders')
                })

        else:
            return JsonResponse({
                'status': 'info',
                'message': f"Order {order.order_id} is already canceled."
            })

    return redirect('user_orders')

################################################################################################################################
@login_required
def user_single_item_cancel(request, order_id, order_item_id):
    if request.method == "POST":
        # Fetch the order and order item
        order_detail = get_object_or_404(OrderDetails, order_id=order_id, user=request.user)
        order_item = get_object_or_404(OrderItem, order=order_detail, id=order_item_id)

        # Prevent cancellation if the item or order has already shipped
        if order_item.order_status in ['Shipped', 'Delivered'] or order_detail.order_status in ['Shipped', 'Delivered']:
            messages.error(request, "You cannot cancel items from an order that has already been shipped or delivered.")
            return redirect('user_orders', order_id=order_id)

        # Calculate refund amount
        refund_amount = order_item.total_price

        # Update the order item status to canceled
        order_item.is_canceled = True
        order_item.order_status = 'Canceled'
        order_item.save()

        # Check if all items in the order are canceled
        all_items_canceled = not OrderItem.objects.filter(order=order_detail, is_canceled=False).exists()

        if all_items_canceled:
            # Update order status to canceled
            order_detail.order_status = 'Canceled'
            order_detail.is_canceled = True
            order_detail.cancel_date = now()
            order_detail.cancel_description = f"Order {order_id} canceled by user. All items were canceled."
        else:
            # Adjust the total order amount for remaining items
            order_detail.total_amount -= refund_amount
            order_detail.cancel_description = f"Item {order_item_id} canceled by user."

        # Handle refund logic
        if order_detail.payment_method == 'ONLINE':
            try:
                wallet = WalletTable.objects.get(user=request.user)
                wallet.update_balance(
                    transaction_type='refund',
                    amount=refund_amount,
                    description=f"Refund for canceled item in Order {order_id}"
                )
                order_detail.is_refund = True
                order_detail.refund_date = now()
                messages.success(request, f"₹{refund_amount:.2f} has been refunded to your wallet.")
            except WalletTable.DoesNotExist:
                messages.error(request, "Refund failed: Wallet not found.")
        elif order_detail.payment_method == 'COD':
            messages.success(request, f"The total amount for Order {order_id} has been updated.")

        # Save changes to the order
        order_detail.save()

        messages.success(request, f"Item {order_item_id} has been successfully canceled.")
    return redirect('user_orders', order_id=order_id)


################################################################################################################################

@csrf_exempt
def verify_payment(request):
    if request.method == 'POST':
        try:
            payment_id = request.POST.get('razorpay_payment_id')
            razorpay_order_id = request.POST.get('razorpay_order_id')
            signature = request.POST.get('razorpay_signature')
            
            params_dict = {
                'razorpay_payment_id': payment_id,
                'razorpay_order_id': razorpay_order_id,
                'razorpay_signature': signature
            }
            
            try:
                # Verify payment signature
                razorpay_client.utility.verify_payment_signature(params_dict)
                
                # Get and update the order
                order = OrderDetails.objects.get(razorpay_order_id=razorpay_order_id)
                order.razorpay_payment_id = payment_id
                order.save()
                
                # Clear the cart after successful payment
                CartTable.objects.filter(user=order.user).delete()
                
                redirect_url = request.build_absolute_uri(
                    reverse('order_success', kwargs={'order_id': order.order_id})
                )
                return JsonResponse({
                    'status': 'success',
                    'message': 'Payment verified successfully',
                    'redirect_url': redirect_url
                })
                
            except razorpay.errors.SignatureVerificationError:
                # Payment verification failed
                order = OrderDetails.objects.get(razorpay_order_id=razorpay_order_id)
                order.order_status = 'Canceled'
                order.cancel_description = "Payment verification failed"
                order.save()
                
                # Restore stock quantities
                order_items = OrderItem.objects.filter(order=order)
                for item in order_items:
                    book = item.book
                    book.stock_quantity += item.quantity
                    book.save()
                
                return JsonResponse({
                    'status': 'error',
                    'message': 'Payment verification failed'
                })
                
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Payment verification failed: {str(e)}'
            })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    })

########################################################################################################################################