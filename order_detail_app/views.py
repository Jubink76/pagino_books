from django.shortcuts import render,redirect,get_object_or_404
from django.contrib import messages
from adminside_app.models import BookTable
from user_profile_app.models import AddressTable,WalletTable, WalletTransaction
from user_side_app.models import CartTable
from .models import OrderDetails, OrderItem,CouponTable,CouponUsage,ReturnRequest,ReturnItem,ReviewTable,OrderAddress
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
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import os
from io import BytesIO
import textwrap
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
                # Get the original address
                original_address = AddressTable.objects.get(id=address_id)
                
                # Create a permanent copy of the address with all fields
                order_address = OrderAddress.objects.create(
                    address_name=original_address.address_name,
                    street_name=original_address.street_name,
                    building_no=original_address.building_no,
                    landmark=original_address.landmark,
                    city=original_address.city,
                    pincode=original_address.pincode,
                    address_phone=original_address.address_phone,
                    state=original_address.state,
                    address_type=original_address.address_type
                )
                
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

                # Restrict COD for orders >= ₹1000
                if payment_method == 'COD' and grand_total >= 1000:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Cash on Delivery is not available for orders above ₹1000. Please choose Online Payment or Wallet.'
                    })
                
                 # Initialize discount details
                discount_amount = 0
                applied_coupon = None
                has_offer = False
                applied_offer = None


                # Check for applied offers in cart items
                for cart_item in cart_items:
                    if cart_item.book.applied_offer:
                        has_offer = True
                        applied_offer = cart_item.book.applied_offer
                        break


                # Apply coupon if provided
                if coupon_code:
                    try:
                        coupon = CouponTable.objects.get(code=coupon_code, is_active=True)
                        
                        # Check if user has already used this coupon maximum times
                        usage_count = CouponUsage.objects.filter(
                            user=request.user,
                            coupon=coupon,
                            is_used=True  # Add this field to CouponUsage model
                        ).count()
                        
                        if usage_count >= coupon.max_uses_per_user:  # Add this field to Coupon model
                            return JsonResponse({
                                'status': 'error', 
                                'message': 'You have already used this coupon the maximum number of times.'
                            })
                        
                        # Calculate discount
                        if coupon.coupon_type == 'PERCENTAGE':
                            discount_amount = grand_total * (coupon.discount_value / 100)
                        elif coupon.coupon_type == 'FIXED':
                            discount_amount = coupon.discount_value
                        else:
                            return JsonResponse({'status': 'error', 'message': 'Invalid coupon type.'})

                        # Check if coupon has minimum order amount requirement
                        if grand_total < coupon.minimum_order_amount:  # Add this field to Coupon model
                            return JsonResponse({
                                'status': 'error',
                                'message': f'Minimum order amount of ₹{coupon.minimum_order_amount} required for this coupon.'
                            })

                        applied_coupon = coupon
                        grand_total -= discount_amount

                        if grand_total < 0:
                            grand_total = 0

                        # Create new coupon usage record
                        CouponUsage.objects.create(
                            user=request.user,
                            coupon=coupon,
                            is_used=True,
                            used_at=timezone.now()
                        )

                    except coupon.DoesNotExist:
                        return JsonResponse({'status': 'error', 'message': 'Invalid or expired coupon.'})

                    
                # Create main order
                order = OrderDetails.objects.create(
                    order_id=single_order_id,
                    user=request.user,
                    address=original_address,
                    delivery_address=order_address,
                    payment_method=payment_method,
                    total_amount=grand_total,
                    order_status='Ordered' if payment_method != 'COD' else 'Pending',
                    coupon_applied=bool(applied_coupon),
                    coupon=applied_coupon,
                    offer_applied=has_offer,
                    offer=applied_offer
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

            OrderItem.objects.filter(order=order).update(
                order_status='Canceled',
                is_canceled=True
            )

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
        try:
            # Get the order and item details
            order_detail = get_object_or_404(OrderDetails, order_id=order_id, user=request.user)
            order_item = get_object_or_404(OrderItem, order=order_detail, id=order_item_id)

            # Prevent cancellation if the item or order is in an unchangeable state
            if order_item.order_status in ['Shipped', 'Delivered']:
                return JsonResponse({
                    'status': 'error',
                    'message': "You cannot cancel items that are already shipped or delivered."
                }, status=400)

            # Calculate refund amount
            refund_amount = Decimal(order_item.total_price)
            coupon_applied = order_detail.coupon if hasattr(order_detail, 'coupon') else None

            with transaction.atomic():
                # Cancel the specific item
                order_item.is_canceled = True
                order_item.order_status = 'Canceled'
                order_item.save()

                # Check for remaining active items in the order
                remaining_items = OrderItem.objects.filter(order=order_detail, is_canceled=False)

                # Adjust total amount and handle coupon usage if necessary
                total_remaining_amount = sum(item.total_price for item in remaining_items)
                if coupon_applied and total_remaining_amount < coupon_applied.min_purchase_amount:
                    discount_lost = coupon_applied.discount_value
                    refund_amount -= discount_lost
                    coupon_usage = CouponUsage.objects.filter(user=request.user, coupon=coupon_applied).first()
                    if coupon_usage:
                        coupon_usage.delete()

                # If no active items remain, cancel the entire order
                if not remaining_items.exists():
                    order_detail.order_status = 'Canceled'
                    order_detail.is_canceled = True
                    order_detail.cancel_date = now()
                    order_detail.cancel_description = f"Order {order_id} canceled as all items were canceled."
                else:
                    # Adjust the order's total amount
                    order_detail.total_amount -= refund_amount
                    order_detail.cancel_description = f"Item {order_item_id} canceled by user."

                order_detail.save()

                # Handle refund for ONLINE payments
                if order_detail.payment_method == 'ONLINE':
                    wallet, _ = WalletTable.objects.get_or_create(user=request.user)
                    wallet.available_balance += refund_amount
                    wallet.save()
                    WalletTransaction.objects.create(
                        wallet=wallet,
                        transaction_type='refund',
                        transaction_amount=refund_amount,
                        description=f"Refund for canceled item in Order {order_id}",
                        transaction_time=now()
                    )

            return JsonResponse({
                'status': 'success',
                'message': f"Item {order_item_id} has been successfully canceled.",
                'item_id': order_item_id,  # For frontend updates
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': "Something went wrong. Please try again later."
            }, status=500)

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
def return_request(request, order_id):
    order = get_object_or_404(OrderDetails, order_id=order_id, user=request.user)

    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        item_ids = request.POST.getlist('items[]')
        
        # Check if order has only one item or if entire order checkbox is checked
        total_items = order.orderitem_set.count()
        return_entire_order = 'entire_order' in request.POST or total_items == 1

        # Validation
        errors = []
        if not reason:
            errors.append({'field': 'reason', 'message': "Reason for return is required."})

        # Only validate item selection if there are multiple items
        if total_items > 1:
            if not return_entire_order and not item_ids:
                errors.append({'field': 'items', 'message': "Select at least one item to return or choose 'Return Entire Order'."})

            if item_ids:
                valid_item_ids = order.orderitem_set.values_list('id', flat=True)
                try:
                    for item_id in item_ids:
                        if int(item_id) not in valid_item_ids:
                            errors.append({'field': 'items', 'message': f"Invalid item ID: {item_id}."})
                except ValueError:
                    errors.append({'field': 'items', 'message': "One or more item IDs are invalid."})

        if errors:
            return JsonResponse({'status': 'error', 'errors': errors}, status=400)

        # Create ReturnRequest and ReturnItems
        with transaction.atomic():
            return_request = ReturnRequest.objects.create(
                order=order,
                user=request.user,
                reason=reason,
                return_entire_order=return_entire_order
            )

            if return_entire_order or total_items == 1:
                # Return all items if it's entire order return or single item order
                for item in order.orderitem_set.all():
                    ReturnItem.objects.create(
                        return_request=return_request,
                        order_item=item,
                        reason=reason
                    )
            else:
                # Return selected items for multiple item orders
                for item_id in item_ids:
                    item = get_object_or_404(OrderItem, id=item_id, order=order)
                    ReturnItem.objects.create(
                        return_request=return_request,
                        order_item=item,
                        reason=reason
                    )

        return JsonResponse({
            'status': 'success',
            'message': "Your return request has been submitted successfully.",
            'redirect_url': reverse('user_orders')
        })

    return JsonResponse({'status': 'error', 'message': "Invalid request method."}, status=405)

#############################################################################################################################

def approve_return_request(request, return_request_id):
    if request.method == "POST":
        return_request = get_object_or_404(ReturnRequest, id=return_request_id)

        # Check if return request is already processed
        if return_request.status != 'Pending':
            return JsonResponse({
                'status': 'error',
                'message': "This return request has already been processed."
            }, status=400)

        try:
            # Process refund
            with transaction.atomic():
                order = return_request.order
                total_refund_amount = Decimal(order.total_amount if return_request.return_entire_order else 0)

                # Calculate refund for selected items if not entire order
                if not return_request.return_entire_order:
                    items_to_return = return_request.items.all()
                    total_refund_amount = sum(item.order_item.total_price for item in items_to_return)

                # Update wallet
                wallet, created = WalletTable.objects.get_or_create(user=order.user)
                wallet.available_balance += total_refund_amount
                wallet.save()

                # Log transaction
                WalletTransaction.objects.create(
                    wallet=wallet,
                    transaction_type='refund',
                    transaction_amount=total_refund_amount,
                    description=f"Refund for returned order {order.order_id}",
                    transaction_time=now()
                )

                # Update order and return request
                return_request.status = 'Approved'
                return_request.processed_at = now()
                return_request.save()

                order.order_status = 'Returned'
                order.is_returned = True
                order.is_refund = True
                order.refund_date = now()
                order.save()

                return JsonResponse({
                    'status': 'success',
                    'message': f"₹{total_refund_amount:.2f} has been refunded to the user's wallet.",
                })

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f"An error occurred while processing the refund: {str(e)}."
            }, status=500)

    return JsonResponse({'status': 'error', 'message': "Invalid request method."}, status=405)

#############################################################################################################################

def reject_return_request(request, return_request_id):
    if request.method == "POST":
        return_request = get_object_or_404(ReturnRequest, id=return_request_id)

        # Check if return request is already processed
        if return_request.status != 'Pending':
            return JsonResponse({
                'status': 'error',
                'message': "This return request has already been processed."
            }, status=400)

        # Mark return request as Rejected
        return_request.status = 'Rejected'
        return_request.processed_at = now()
        return_request.save()

        return JsonResponse({
            'status': 'success',
            'message': "The return request has been rejected."
        })

    return JsonResponse({'status': 'error', 'message': "Invalid request method."}, status=405)

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

            if total_amount < coupon.min_purchase_amount:
                return JsonResponse({'status': 'error', 'message': f'Minimum purchase amount is ₹{coupon.min_purchase_amount}.'})
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

#################################################################################################################################

def generate_invoice(request, order_id):
    try:
        # Fetch the order details
        order = OrderDetails.objects.get(order_id=order_id)
        order_items = OrderItem.objects.filter(order=order)
        total_product_amount = sum(item.total_price for item in order_items)
        refunded_amount = 0
        for item in order_items:
            if item.is_canceled:
                refunded_amount += item.total_price  # Refund based on the total price of the canceled item

        # Calculate the remaining amount after refund
        remaining_amount = total_product_amount - refunded_amount
        if order.coupon_applied:
            amount_after_offers_coupon = total_product_amount-order.coupon.discount_value
        # Create PDF
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        # Title and Header (Centered)
        p.setFont("Helvetica-Bold", 24)
        p.drawCentredString(width / 2, height - 30, f"Pagino Books")
        p.setFont("Helvetica-Bold", 14)
        p.drawCentredString(width / 2, height - 60, f"Invoice for Order-{order_id}")

        address_components = []
        if order.delivery_address.street_name:
            address_components.append(order.delivery_address.street_name)
        if order.delivery_address.building_no:
            address_components.append(order.delivery_address.building_no)
        if order.delivery_address.landmark:
            address_components.append(f"Near {order.delivery_address.landmark}")
        if order.delivery_address.city:
            address_components.append(order.delivery_address.city)
        if order.delivery_address.state:
            address_components.append(order.delivery_address.state)
        if order.delivery_address.pincode:
            address_components.append(order.delivery_address.pincode)

        formatted_address = ", ".join(filter(None, address_components))


        # Customer Info (Centered)
        p.setFont("Helvetica", 12)
        y_pos = height - 80
        p.drawCentredString(width / 2, y_pos, f"Customer: {order.user.username} ({order.user.phone_number})")
        y_pos -= 25

        formatted_address = f"Shipping Address: {formatted_address}"
        if len(formatted_address) > 60:
            chunks = [formatted_address[i:i+60] for i in range(0, len(formatted_address), 60)]
            for chunk in chunks:
                p.drawCentredString(width / 2, y_pos, chunk)
                y_pos -= 20
        else:
            p.drawCentredString(width / 2, y_pos, formatted_address)
            y_pos -= 20

        y_pos -= 20 


        # Draw a Line Separator
        p.setLineWidth(1)
        p.line(50, y_pos, width - 50, y_pos)
        y_pos -= 30

        # Order Summary Header
        p.setFont("Helvetica-Bold", 12)
        # Center the column headers
        p.drawString(100, y_pos, "Item Description")
        p.drawString(350, y_pos, "Quantity")
        p.drawString(450, y_pos, "Price")
        y_pos -= 20

        p.setFont("Helvetica", 10)
        for item in order_items:
            p.drawString(100, y_pos, f"{item.book.book_name}")
            p.drawRightString(360, y_pos, str(item.quantity))  # Right-align quantity
            p.drawRightString(500, y_pos, f"₹{item.price_per_item:,.2f}")  # Right-align price
            y_pos -= 20

        y_pos -= 10

        # Draw a Line Separator
        p.setLineWidth(1)
        p.line(50, y_pos, width - 50, y_pos)
        y_pos -= 30

        # Payment Details
        def draw_info_line(label, value, bold_value=False):
            nonlocal y_pos
            p.setFont("Helvetica-Bold", 12)
            p.drawString(100, y_pos, label)
            p.setFont("Helvetica-Bold" if bold_value else "Helvetica", 12)
            p.drawString(300, y_pos, value)
            y_pos -= 25  # Consistent spacing between lines

        # Payment Details
        draw_info_line("Payment Method:", str(order.payment_method))
        
        payment_status = "Completed" if order.payment_method in ['ONLINE', 'WALLET'] \
                        else "Paid" if order.order_status == "Delivered" \
                        else "Pending"
        draw_info_line("Payment Status:", payment_status)
        
        # Amount Details
        draw_info_line("Total Amount:", f"₹{total_product_amount:,.2f}")
        if amount_after_offers_coupon:
            draw_info_line("Amount Paid:", f"₹{amount_after_offers_coupon:,.2f}", True)

        if refunded_amount > 0:
            draw_info_line("Refunded Amount:", f"₹{refunded_amount:,.2f}")
            draw_info_line("Remaining Amount:", f"₹{remaining_amount:,.2f}", True)

        y_pos -= 10  # Extra space before discount section

        # Discount Section
        if order.coupon_applied:
            draw_info_line("Coupon Applied:", 
                          f"Code: {order.coupon.code} - {order.coupon.discount_value} {order.coupon.coupon_type}")
        else:
            draw_info_line("Coupon Status:", "No Coupon Applied")

        if order.offer_applied:
            draw_info_line("Offer Applied:", 
                          f"Offer: {order.offer.offer_name} - {order.offer.discount_value}")
        else:
            draw_info_line("Offer Status:", "No Offer Applied")

        # Cancellation Details
        if order.is_canceled:
            y_pos -= 10  # Extra space before cancellation details
            p.setFont("Helvetica-Bold", 12)
            p.drawString(100, y_pos, "Order Canceled")
            y_pos -= 20
            p.setFont("Helvetica", 12)
            p.drawString(100, y_pos, f"Refunded Amount: ₹{order.total_amount:,.2f}")
            y_pos -= 20
            p.drawString(100, y_pos, f"Reason: {order.cancel_description}")
            y_pos -= 20
            p.drawString(100, y_pos, f"Refund Date: {order.refund_date}")
            y_pos -= 30

        # Footer
        p.setFont("Helvetica", 10)
        p.drawCentredString(width / 2, 30, "Thank you for shopping with us!")

        # Save PDF
        p.save()
        buffer.seek(0)


        # Define the path for saving the PDF in the invoices folder
        pdf_name = f"invoice_{order_id}.pdf"
        
        # Use os.path.join to create the correct file path
        media_path = os.path.join('media', 'invoices')  # Path to the 'invoices' folder
        pdf_path = os.path.join(media_path, pdf_name)

        # Ensure the directory exists
        os.makedirs(media_path, exist_ok=True)

        # Save the PDF to the 'invoices' folder
        with open(pdf_path, 'wb') as f:
            f.write(buffer.getvalue())

        buffer.close()

        # Return the URL to access the PDF
        return JsonResponse({
            'status': 'success',
            'message': 'Invoice generated successfully!',
            'file_url': f'/media/invoices/{pdf_name}'  # URL to download the invoice
        })

    except OrderDetails.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Order not found.'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    

############################################################################################################################################

@login_required
def submit_review(request, order_id):
    # Get the order
    order = get_object_or_404(OrderDetails, order_id=order_id, user=request.user)
    
    if request.method == 'POST':
        # Get review data
        rating = request.POST.get('rating')
        review = request.POST.get('review', '').strip()
        book_id = request.POST.get('book_id')
        # Validation
        errors = []
        if not rating or not review:
            errors.append({'field': 'rating', 'message': 'Rating and review are required.'})
        
        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                errors.append({'field': 'rating', 'message': 'Rating must be between 1 and 5.'})
        except ValueError:
            errors.append({'field': 'rating', 'message': 'Invalid rating.'})
        
        if errors:
            return JsonResponse({'status': 'error', 'errors': errors}, status=400)
        
        if not book_id:
            return JsonResponse({'status': 'error', 'message': 'Book ID is missing.'}, status=400)

        try:
            book_id = int(book_id)
        except ValueError:
            return JsonResponse({'status': 'error', 'message': 'Invalid Book ID provided.'}, status=400)
        
        book = get_object_or_404(BookTable, id=book_id)

        with transaction.atomic():
            ReviewTable.objects.create(
                order=order,
                book=book,
                rating=rating,
                review=review,
                user=request.user
            )

        return JsonResponse({
            'status': 'success',
            'message': 'Your review has been submitted successfully.',
            'redirect_url': reverse('user_orders')
        })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)

###################################################################################################################
