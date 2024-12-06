from django.shortcuts import render,redirect,get_object_or_404
from django.contrib import messages
from user_profile_app.models import AddressTable,WalletTable, WalletTransaction
from user_side_app.models import CartTable
from .models import OrderDetails, OrderItem,CouponTable,CouponUsage
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
        coupon_code = request.session.get('coupon_code', None)
        print(coupon_code)
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
                
                 # Initialize discount details
                discount_amount = 0
                applied_coupon = None

                # Apply coupon if provided
                if coupon_code:
                    coupon_usage = CouponUsage.objects.filter(
                        user=request.user,
                        coupon__code=coupon_code
                    ).last()

                    if coupon_usage and coupon_usage.coupon.is_active:
                        coupon = coupon_usage.coupon
                        if coupon.coupon_type == 'PERCENTAGE':
                            discount_amount = grand_total * (coupon.discount_value / 100)
                        elif coupon.coupon_type == 'fixed':
                            discount_amount = coupon.discount_value
                        else:
                            return JsonResponse({'status': 'error', 'message': 'Invalid coupon type.'})

                        applied_coupon = coupon
                        grand_total -= discount_amount

                        if grand_total < 0:
                            grand_total = 0  # Ensure grand total doesn't go negative
                    else:
                        return JsonResponse({'status': 'error', 'message': 'Invalid or expired coupon.'})

                    
                # Create main order
                order = OrderDetails.objects.create(
                    order_id=single_order_id,
                    user=request.user,
                    address=address,
                    payment_method=payment_method,
                    total_amount=grand_total,
                    order_status='Ordered'
                )

                # Create order items
                for cart_item in cart_items:

                    OrderItem.objects.create(
                        order=order,
                        book=cart_item.book,
                        quantity=cart_item.quantity,
                        price_per_item=cart_item.book.offer_price,
                        total_price=cart_item.quantity * cart_item.book.offer_price
                    )
                    
                    # Update stock after order is created
                    if cart_item.book.stock_quantity >= cart_item.quantity:
                        cart_item.book.stock_quantity -= cart_item.quantity
                        cart_item.book.save()
                    elif cart_item.book.stock_quantity == 0:
                        cart_item.book.stock_quantity = 0
                    else:
                        raise ValueError(f"Not enough stock for {cart_item.book.book_name}")


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
                    
                    # For WALLET payments
                elif payment_method == 'WALLET':
                    # Check if the user has enough balance in their wallet
                    wallet = request.user.wallet
                    if wallet.available_balance < grand_total:
                        return JsonResponse({'status': 'error', 'message': 'Insufficient amount in your wallet. Try another payment method.'})

                    # Deduct the amount from the user's wallet
                    wallet.available_balance -= grand_total
                    wallet.save()

                    # Create a wallet transaction
                    WalletTransaction.objects.create(
                        wallet=wallet,
                        transaction_type='deduct',
                        transaction_amount=grand_total,
                        description=f"Order {order.order_id} payment deduction",
                        transaction_time=timezone.now()
                    )

                    # Clear cart immediately after successful wallet payment
                    cart_items.delete()

                    # Update order status
                    order.order_status = 'Ordered'
                    order.save()

                    redirect_url = request.build_absolute_uri(
                        reverse('order_success', kwargs={'order_id': order.order_id})
                    )
                    return JsonResponse({
                        'status': 'success',
                        'payment_method': 'WALLET',
                        'message': 'Order placed successfully using wallet!',
                        'redirect_url': redirect_url
                    })

                    # FOR COD PAYEMENTS
                else:
                    # Clear cart immediately
                    cart_items.delete()
                    
                    if payment_method == 'COD':
                        order.order_status = 'Ordered'  # COD starts as Pending
                        order.save()

                        redirect_url = request.build_absolute_uri(
                            reverse('order_success', kwargs={'order_id': order.order_id})
                        )
                        return JsonResponse({
                            'status': 'success',
                            'payment_method': 'COD',
                            'message': 'Order placed successfully with Cash on Delivery!',
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
        # Retrieve the order
        order = get_object_or_404(OrderDetails, order_id=order_id, user=request.user)

        # Check if the order is already canceled
        if order.order_status != 'Canceled':
            # Update order status
            order.order_status = 'Canceled'
            order.is_canceled = True
            order.save()

            # Handle refund if payment method is ONLINE
            if order.payment_method in ['ONLINE', 'WALLET']:
                # Get or create the user's wallet
                wallet, created = WalletTable.objects.get_or_create(user=request.user)

                # Update wallet balance
                wallet.available_balance += order.total_amount
                wallet.save()

                # Log the transaction
                WalletTransaction.objects.create(
                    wallet=wallet,
                    transaction_type='refund',
                    transaction_amount=order.total_amount,
                    description=f"Refund for canceled order {order.order_id}",
                    transaction_time=timezone.now()
                )

                return JsonResponse({
                    'status': 'success',
                    'message': f"Order {order.order_id} has been canceled and refunded to your wallet.",
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

        # Prevent cancellation if the item or order has already shipped or delivered
        if order_item.order_status in ['Shipped', 'Delivered'] or order_detail.order_status in ['Shipped', 'Delivered']:
            return JsonResponse({
                'status': 'error',
                'message': "You cannot cancel items from an order that has already been shipped or delivered."
            }, status=400)

        # Calculate refund amount
        refund_amount = Decimal(order_item.total_price)

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
                # Retrieve or create the user's wallet
                wallet, _ = WalletTable.objects.get_or_create(user=request.user)

                # Update wallet balance
                wallet.available_balance += refund_amount
                wallet.save()

                # Log the transaction
                WalletTransaction.objects.create(
                    wallet=wallet,
                    transaction_type='refund',
                    transaction_amount=refund_amount,
                    description=f"Refund for canceled item in Order {order_id}",
                    transaction_time=now()
                )

                order_detail.is_refund = True
                order_detail.refund_date = now()

                return JsonResponse({
                    'status': 'success',
                    'message': f"₹{refund_amount:.2f} has been refunded to your wallet.",
                    'order_status': order_detail.order_status,
                    'order_item_status': order_item.order_status,
                    'refund_amount': float(refund_amount),
                })
            except WalletTable.DoesNotExist:
                return JsonResponse({
                    'status': 'error',
                    'message': "Refund failed: Wallet not found."
                }, status=500)
        elif order_detail.payment_method == 'COD':
            return JsonResponse({
                'status': 'success',
                'message': f"Item {order_item_id} has been successfully canceled. The total amount for Order {order_id} has been updated.",
                'order_status': order_detail.order_status,
                'order_item_status': order_item.order_status,
            })

        # Save changes to the order
        order_detail.save()

        return JsonResponse({
            'status': 'success',
            'message': f"Item {order_item_id} has been successfully canceled.",
            'order_status': order_detail.order_status,
            'order_item_status': order_item.order_status,
        })

    return JsonResponse({
        'status': 'error',
        'message': "Invalid request method."
    }, status=405)

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

@login_required
def return_order(request, order_id):
    if request.method == "POST":
        
        order = get_object_or_404(OrderDetails, order_id=order_id, user=request.user)

        if order.order_status != 'Delivered':
            return JsonResponse({
                'status': 'error',
                'message': "Only delivered orders can be returned."
            }, status=400)

        total_refund_amount = Decimal(order.total_amount)

        try:
            
            wallet, created = WalletTable.objects.get_or_create(user=request.user)

            wallet.available_balance += total_refund_amount
            wallet.save()

            # Log the transaction for the refund
            WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type='refund',
                transaction_amount=total_refund_amount,
                description=f"Refund for returned order {order.order_id}",
                transaction_time=now()
            )

            order.is_refund = True
            order.refund_date = now()  
            order.save()

            return JsonResponse({
                'status': 'success',
                'message': f"₹{total_refund_amount:.2f} has been refunded to your wallet.",
                'order_status': order.order_status,
                'refund_amount': float(total_refund_amount),
            })

        except WalletTable.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': "Refund failed: Wallet not found."
            }, status=500)

    return JsonResponse({
        'status': 'error',
        'message': "Invalid request method."
    }, status=405)

#############################################################################################################################

def apply_coupon(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            coupon_code = data.get('coupon_code')

            coupon = CouponTable.objects.filter(code=coupon_code, is_active=True).first()

            if not coupon:
                return JsonResponse({'status': 'error', 'message': 'Invalid or expired coupon.'})


            cart_items = CartTable.objects.filter(user=request.user)
            total_amount = sum(item.quantity * item.book.offer_price for item in cart_items)

            if coupon.coupon_type == 'PERCENTAGE':
                discount_amount = total_amount * (coupon.discount_value / 100)
                new_total = total_amount - discount_amount
            elif coupon.coupon_type == 'fixed':
                discount_amount = coupon.discount_value
                new_total = total_amount - discount_amount
            else:
                return JsonResponse({'status': 'error', 'message': 'Invalid coupon type.'})

            CouponUsage.objects.create(
                user=request.user,
                coupon=coupon,
                discount_value=round(discount_amount, 2),
                used_at=now()
            )

            # Store the applied coupon code in the session
            request.session['coupon_code'] = coupon_code


            return JsonResponse({
                'status': 'success',
                'new_total': round(new_total, 2),
                'discount_amount': round(discount_amount, 2)
            })

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})
###########################################################################################################################

def remove_coupon(request):
    if request.method == 'POST':
        try:
            coupon_usage = CouponUsage.objects.filter(user=request.user).last()

            if not coupon_usage:
                return JsonResponse({'status': 'error', 'message': 'No coupon applied.'})

            cart_items = CartTable.objects.filter(user=request.user)
            original_total_amount = sum(item.quantity * item.book.offer_price for item in cart_items)

            coupon_usage.delete()

            if 'coupon_code' in request.session:
                del request.session['coupon_code']

            return JsonResponse({
                'status': 'success',
                'original_total': round(original_total_amount, 2),
                'discount_amount': 0
            })

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})