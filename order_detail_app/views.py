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
        # Payment verification callback handling
        razorpay_payment_id = request.POST.get('razorpay_payment_id')
        razorpay_order_id = request.POST.get('razorpay_order_id')
        razorpay_signature = request.POST.get('razorpay_signature')
        
        if razorpay_payment_id and razorpay_order_id and razorpay_signature:
            try:
                params_dict = {
                    'razorpay_payment_id': razorpay_payment_id,
                    'razorpay_order_id': razorpay_order_id,
                    'razorpay_signature': razorpay_signature
                }
                
                try:
                    razorpay_client.utility.verify_payment_signature(params_dict)
                except Exception as e:
                    try:
                        order = OrderDetails.objects.get(razorpay_order_id=razorpay_order_id)
                        if order.coupon:
                            # Delete the coupon usage record if payment failed
                            CouponUsage.objects.filter(
                                user=request.user,
                                coupon=order.coupon,
                                is_used=False
                            ).delete()
                            # Restore coupon to session
                            request.session['temp_coupon'] = {
                                'coupon_id': order.coupon.id,
                                'code': order.coupon.code,
                                'discount_amount': order.coupon_discount_amount
                            }
                            request.session.modified = True
                        order.delete()
                    except OrderDetails.DoesNotExist:
                        pass
                    
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Payment verification failed. Please try again.'
                    })
                
                try:
                    order = OrderDetails.objects.get(razorpay_order_id=razorpay_order_id)
                    
                    # Update coupon usage to mark as used after successful payment
                    if order.coupon:
                        coupon_usage = CouponUsage.objects.get(
                            user=request.user,
                            coupon=order.coupon,
                            is_used=False  # Get the pending usage record
                        )
                        coupon_usage.is_used = True
                        coupon_usage.save()
                        
                        if 'temp_coupon' in request.session:
                            del request.session['temp_coupon']
                            request.session.modified = True
                    
                    order.razorpay_payment_id = razorpay_payment_id
                    order.order_status = 'Ordered'
                    order.save()
                    
                    CartTable.objects.filter(user=request.user).delete()
                    
                    return JsonResponse({
                        'status': 'success',
                        'message': 'Payment successful and order created!',
                        'redirect_url': request.build_absolute_uri(
                            reverse('order_success', kwargs={'order_id': order.order_id})
                        )
                    })
                except OrderDetails.DoesNotExist:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Order not found'
                    })
                    
            except Exception as e:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Payment verification failed: {str(e)}'
                })
        
        # Initial order creation
        address_id = request.POST.get("savedAddress")
        payment_method = request.POST.get("payment")
        temp_coupon = request.session.get('temp_coupon')
        
        if not address_id:
            return JsonResponse({'status': 'error', 'message': 'Please select a delivery address'})
        if not payment_method:
            return JsonResponse({'status': 'error', 'message': 'Please select a payment method'})
        if payment_method not in ['COD', 'ONLINE', 'WALLET']:
            return JsonResponse({'status': 'error', 'message': 'Invalid payment method selected.'})
            
        try:
            with transaction.atomic():
                # Get address and create order address
                original_address = AddressTable.objects.get(id=address_id)
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
                
                # Calculate total amount
                grand_total = sum(item.quantity * item.book.offer_price for item in cart_items)

                # Apply coupon if available in session
                applied_coupon = None
                coupon_discount_amount = 0
                if temp_coupon:
                    try:
                        coupon = CouponTable.objects.get(id=temp_coupon['coupon_id'], is_active=True)
                        
                        # Check if coupon has already been used by this user
                        usage_count = CouponUsage.objects.filter(
                            user=request.user,
                            coupon=coupon,
                            is_used=True
                        ).count()
                        
                        if usage_count >= coupon.max_uses_per_user:
                            # Remove coupon from session if already used
                            if 'temp_coupon' in request.session:
                                del request.session['temp_coupon']
                                request.session.modified = True
                            return JsonResponse({
                                'status': 'error',
                                'message': 'This coupon has already been used.'
                            })
                        
                        if grand_total >= coupon.min_purchase_amount:
                            if coupon.coupon_type == 'percentage':
                                coupon_discount_amount = grand_total * (coupon.discount_value / 100)
                            else:  # FIXED
                                coupon_discount_amount = coupon.discount_value
                                
                            grand_total -= coupon_discount_amount
                            applied_coupon = coupon
                            
                    except CouponTable.DoesNotExist:
                        if 'temp_coupon' in request.session:
                            del request.session['temp_coupon']
                            request.session.modified = True
                
                # Create order
                order = OrderDetails.objects.create(
                    order_id=generate_order_id(),
                    user=request.user,
                    address=original_address,
                    delivery_address=order_address,
                    payment_method=payment_method,
                    total_amount=grand_total,
                    order_status='Ordered',
                    coupon=applied_coupon,
                    coupon_applied=bool(applied_coupon),
                    coupon_discount=coupon_discount_amount
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
                
                # Create coupon usage record (initially not marked as used)
                if applied_coupon:
                    coupon_usage = CouponUsage.objects.create(
                        user=request.user,
                        coupon=applied_coupon,
                        discount_value=coupon_discount_amount,
                        is_used=False  # Will be marked True after successful payment
                    )
                
                # Handle different payment methods
                if payment_method == 'ONLINE':
                    try:
                        razorpay_order = razorpay_client.order.create({
                            'amount': int(grand_total * 100),
                            'currency': 'INR',
                            'payment_capture': '1'
                        })
                        order.razorpay_order_id = razorpay_order['id']
                        order.save()
                        
                        return JsonResponse({
                            'status': 'success',
                            'payment_method': 'ONLINE',
                            'razorpay_key': settings.RAZORPAY_KEY_ID,
                            'razorpay_order_id': razorpay_order['id'],
                            'amount': int(grand_total * 100),
                            'currency': 'INR',
                            'customer_name': request.user.username,
                            'email': request.user.email,
                            'phone': request.user.phone if hasattr(request.user, 'phone') else ''
                        })
                    except Exception as e:
                        # Clean up coupon usage if payment creation fails
                        if applied_coupon:
                            CouponUsage.objects.filter(
                                user=request.user,
                                coupon=applied_coupon,
                                is_used=False
                            ).delete()
                        order.delete()
                        raise ValueError(f"Failed to create payment: {str(e)}")
                
                elif payment_method == 'WALLET':
                    wallet = request.user.wallet
                    if wallet.available_balance < grand_total:
                        # Clean up coupon usage if wallet payment fails
                        if applied_coupon:
                            CouponUsage.objects.filter(
                                user=request.user,
                                coupon=applied_coupon,
                                is_used=False
                            ).delete()
                        order.delete()
                        return JsonResponse({
                            'status': 'error',
                            'message': 'Insufficient wallet balance'
                        })
                    
                    wallet.available_balance -= grand_total
                    wallet.save()
                    
                    # Mark coupon as used for wallet payment
                    if applied_coupon:
                        coupon_usage = CouponUsage.objects.get(
                            user=request.user,
                            coupon=applied_coupon,
                            is_used=False
                        )
                        coupon_usage.is_used = True
                        coupon_usage.save()
                        
                        if 'temp_coupon' in request.session:
                            del request.session['temp_coupon']
                            request.session.modified = True
                    
                    order.order_status = 'Ordered'
                    order.save()
                    
                    cart_items.delete()
                    
                    return JsonResponse({
                        'status': 'success',
                        'payment_method': 'WALLET',
                        'message': 'Order placed successfully using wallet!',
                        'redirect_url': request.build_absolute_uri(
                            reverse('order_success', kwargs={'order_id': order.order_id})
                        )
                    })
                
                else:  # COD
                    # Mark coupon as used for COD
                    if payment_method == 'COD' and grand_total > 1000:
                        # Clean up coupon usage if COD is not allowed
                        if applied_coupon:
                            CouponUsage.objects.filter(
                                user=request.user,
                                coupon=applied_coupon,
                                is_used=False
                            ).delete()
                        order.delete()
                        return JsonResponse({
                            'status': 'error',
                            'message': 'Cash on Delivery not available for orders above ₹1000. Please choose another payment method.',
                            'payment_methods': ['WALLET', 'ONLINE']
                        })
                    if applied_coupon:
                        coupon_usage = CouponUsage.objects.get(
                            user=request.user,
                            coupon=applied_coupon,
                            is_used=False
                        )
                        coupon_usage.is_used = True
                        coupon_usage.save()
                        
                        if 'temp_coupon' in request.session:
                            del request.session['temp_coupon']
                            request.session.modified = True
                    
                    order.order_status = 'Ordered'
                    order.save()
                    
                    cart_items.delete()
                    
                    return JsonResponse({
                        'status': 'success',
                        'payment_method': 'COD',
                        'message': 'Order placed successfully with Cash on Delivery!',
                        'redirect_url': request.build_absolute_uri(
                            reverse('order_success', kwargs={'order_id': order.order_id})
                        )
                    })
                    
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
            
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
            # Identify non-canceled items
            non_canceled_items = OrderItem.objects.filter(order=order, is_canceled=False)

            # Calculate the refund amount for non-canceled items
            refund_amount = sum(item.total_price for item in non_canceled_items)

            # Adjust refund amount if coupon or offer was applied
            if order.coupon_applied:
                # Proportionally adjust coupon discount
                total_original_amount = sum(item.total_price for item in order.orderitem_set.all())
                item_proportion = refund_amount / total_original_amount
                refund_amount -= order.coupon_discount * item_proportion

            for item in non_canceled_items:
                book = item.book
                book.stock_quantity += item.quantity
                book.save()

            # Handle refund if payment method is ONLINE
            if order.payment_method in ['ONLINE', 'WALLET']:
                # Get or create the user's wallet
                wallet, created = WalletTable.objects.get_or_create(user=request.user)

                # Update wallet balance with the calculated refund amount
                wallet.available_balance += refund_amount
                wallet.save()

                # Log the transaction
                WalletTransaction.objects.create(
                    wallet=wallet,
                    transaction_type='refund',
                    transaction_amount=refund_amount,
                    description=f"Refund for canceled order {order.order_id}",
                    transaction_time=timezone.now()
                )

            # Update order status for non-canceled items
            non_canceled_items.update(
                order_status='Canceled',
                is_canceled=True
            )

            # Update order total and status
            order.total_amount = Decimal('0.00')
            order.order_status = 'Canceled'
            order.is_canceled = True
            order.save()

            return JsonResponse({
                'status': 'success',
                'message': f"Order {order.order_id} has been canceled. Refund amount: {refund_amount}",
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

            # Validate order_id and order_item_id types if needed
            if not order_id or not order_item_id:
                return JsonResponse({
                    'status': 'error', 
                    'message': 'Invalid order or item ID'
                }, status=400)

            try:
                order_detail = OrderDetails.objects.get(order_id=order_id, user=request.user)
            except OrderDetails.DoesNotExist:
                return JsonResponse({
                    'status': 'error', 
                    'message': 'Order not found'
                }, status=404)

            try:
                order_item = OrderItem.objects.get(order=order_detail, id=order_item_id)
            except OrderItem.DoesNotExist:

                return JsonResponse({
                    'status': 'error', 
                    'message': 'Order item not found'
                }, status=404)

            # Prevent cancellation if item is shipped or delivered
            if order_item.order_status in ['Shipped', 'Delivered']:
                return JsonResponse({
                    'status': 'error',
                    'message': "Cannot cancel shipped or delivered items."
                }, status=400)
            # Get all order items
            all_order_items = OrderItem.objects.filter(order=order_detail)

            total_order_amount = sum(item.total_price for item in all_order_items)

            # Initialize refund amount
            refund_amount = Decimal(order_item.total_price)

            # Handle coupon calculation
            if order_detail.coupon_applied and order_detail.coupon:
                coupon = order_detail.coupon

                # Calculate coupon discount distribution
                if coupon.coupon_type == 'percentage':
                    # Percentage-based coupon
                    coupon_discount = total_order_amount * (coupon.discount_value / Decimal(100))
                    item_proportion = order_item.total_price / total_order_amount
                    item_coupon_discount = coupon_discount * item_proportion
                    refund_amount -= item_coupon_discount
                
                elif coupon.coupon_type == 'fixed':
                    # Fixed amount coupon
                    item_proportion = order_item.total_price / total_order_amount
                    item_coupon_discount = coupon.discount_value * item_proportion
                    refund_amount -= item_coupon_discount
            # Handle offer calculation
            offer = order_item.offer if hasattr(order_item, 'offer') else None

            if offer and offer.is_active:
                if offer.discount_type == 'percentage':
                    original_price = order_item.total_price / (Decimal(1) - (offer.discount_value / Decimal(100)))
                    offer_discount = original_price - order_item.total_price
                    refund_amount = order_item.total_price
                
                elif offer.discount_type == 'fixed':
                    # Adjust refund for fixed amount offer
                    refund_amount = order_item.total_price

            with transaction.atomic():
                # Cancel the specific item
                order_item.is_canceled = True
                order_item.order_status = 'Canceled'
                order_item.save()
                # Recalculate order total and status
                remaining_items = all_order_items.exclude(is_canceled=True)
                
                if not remaining_items.exists():
                    # Entire order canceled
                    order_detail.order_status = 'Canceled'
                    order_detail.is_canceled = True
                    order_detail.cancel_date = now()
                else:
                    # Update order total
                    new_total = sum(item.total_price for item in remaining_items)
                    order_detail.total_amount = new_total

                order_detail.save()

                # Handle refund for ONLINE payments
                if order_detail.payment_method in ['ONLINE', 'WALLET']:
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
                print("wallet transaction ccompleted")
            return JsonResponse({
                'status': 'success',
                'message': f"Item {order_item_id} canceled successfully.",
                'refund_amount': float(refund_amount),
                'item_id': order_item_id
            })

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': "An error occurred. Please try again."
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
            with transaction.atomic():
                order = return_request.order
                
                # Calculate refund amount
                if return_request.return_entire_order:
                    # Entire order return
                    total_refund_amount = order.total_amount
                    order.order_status = 'Returned'
                    order.is_returned = True
                    order.is_refund = True
                    order.refund_date = now()
                    
                    OrderItem.objects.filter(order=order).update(
                        order_status='Returned',
                        is_returned=True
                    )

                    # Handle coupon discount for full order
                    if order.coupon_applied and order.coupon:
                        coupon = order.coupon
                        if coupon.discount_type == 'percentage':
                            coupon_discount = total_refund_amount * (coupon.discount_value / Decimal(100))
                            total_refund_amount -= coupon_discount
                        elif coupon.discount_type == 'fixed':
                            total_refund_amount -= coupon.discount_value

                else:
                    # Partial order return
                    return_items = return_request.items.all()
                    
                    # Calculate total returned items price
                    total_returned_items_price = sum(item.order_item.total_price for item in return_items)
                    total_order_amount = sum(item.total_price for item in order.orderitem_set.all())

                    for return_item in return_items:
                        order_item = return_item.order_item
                        order_item.order_status = 'Returned'
                        order_item.is_returned = True
                        order_item.save()

                    remaining_non_returned_items = order.orderitem_set.exclude(order_status='Returned').count()
                    if remaining_non_returned_items == 0:
                        order.order_status = 'Returned'
                        order.is_returned = True
                        order.is_refund = True
                        order.refund_date = now()
                        order.save()

                        
                    # Handle coupon discount for partial return
                    if order.coupon_applied and order.coupon:
                        coupon = order.coupon
                        
                        if coupon.coupon_type == 'percentage':
                            # Percentage-based coupon
                            coupon_discount = total_order_amount * (coupon.discount_value / Decimal(100))
                            item_proportion = total_returned_items_price / total_order_amount
                            returned_items_coupon_discount = coupon_discount * item_proportion
                            total_returned_items_price -= returned_items_coupon_discount
                        
                        elif coupon.coupon_type == 'fixed':
                            # Fixed amount coupon
                            item_proportion = total_returned_items_price / total_order_amount
                            returned_items_coupon_discount = coupon.discount_value * item_proportion
                            total_returned_items_price -= returned_items_coupon_discount

                    # Handle individual item offers for returned items
                    for return_item in return_items:
                        item = return_item.order_item
                        offer = item.offer if hasattr(item, 'offer') else None
                        
                        if offer and offer.is_active:
                            if offer.discount_type == 'percentage':
                                original_price = item.total_price / (Decimal(1) - (offer.discount_value / Decimal(100)))
                                total_returned_items_price = item.total_price

                    total_refund_amount = total_returned_items_price

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

                # Update order and return request statuses
                return_request.status = 'Approved'
                return_request.processed_at = now()
                return_request.save()

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

            # Check if user has already used this coupon maximum times
            usage_count = CouponUsage.objects.filter(
                user=request.user,
                coupon=coupon,
                is_used=True
            ).count()
            
            if usage_count >= coupon.max_uses_per_user:
                return JsonResponse({
                    'status': 'error', 
                    'message': 'You have already used this coupon the maximum number of times.'
                })

            cart_items = CartTable.objects.filter(user=request.user)
            # Convert Decimal to float
            total_amount = float(sum(item.quantity * item.book.offer_price for item in cart_items))

            if total_amount < float(coupon.min_purchase_amount):
                return JsonResponse({'status': 'error', 'message': f'Minimum purchase amount is ₹{coupon.min_purchase_amount}.'})

            if coupon.coupon_type == 'percentage':
                discount_amount = total_amount * (float(coupon.discount_value) / 100)
                new_total = total_amount - discount_amount
            elif coupon.coupon_type == 'fixed':
                discount_amount = float(coupon.discount_value)
                new_total = total_amount - discount_amount
            else:
                return JsonResponse({'status': 'error', 'message': 'Invalid coupon type.'})
            
            if total_amount < discount_amount:
                return JsonResponse({'status':'error','message': f'Total amount should be greater than ₹{discount_amount}.'})
            
            # Store converted float values in session
            request.session['temp_coupon'] = {
                'code': coupon_code,
                'discount_amount': round(float(discount_amount), 2),
                'original_total': float(total_amount),
                'new_total': round(float(new_total), 2),
                'coupon_id': coupon.id
            }
            request.session.modified = True

            return JsonResponse({
                'status': 'success',
                'new_total': round(float(new_total), 2),
                'discount_amount': round(float(discount_amount), 2)
            })

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})
###########################################################################################################################

def remove_coupon(request):
    if request.method == 'POST':
        try:
            if 'temp_coupon' not in request.session:
                return JsonResponse({'status': 'error', 'message': 'No coupon applied.'})

            # Get the original total from the session
            original_total = request.session['temp_coupon']['original_total']
            
            # Clear coupon data from session
            del request.session['temp_coupon']
            request.session.modified = True

            return JsonResponse({
                'status': 'success',
                'original_total': round(original_total, 2),
                'discount_amount': 0
            })

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})

#################################################################################################################################
def generate_invoice(request, order_id):
    try:
        # Fetch the order details with related data
        order = OrderDetails.objects.select_related(
            'user', 'delivery_address', 'coupon', 'offer'
        ).prefetch_related(
            'orderitem_set__book',
            'orderitem_set__book__product_offer',  # Add prefetch for product offers
            'orderitem_set__book__category__category_offers',  # Add prefetch for category offers
            'returnrequest_set'
        ).get(order_id=order_id)
        
        order_items = OrderItem.objects.filter(order=order)
        total_product_amount = sum(item.total_price for item in order_items)
        
        # Calculate refunds (both cancellations and returns)
        refunded_amount = 0
        return_request = order.returnrequest_set.filter(status='Approved').first()
        
        if return_request:
            if return_request.return_entire_order:
                refunded_amount = total_product_amount
            else:
                returned_items = return_request.items.all()
                refunded_amount = sum(item.order_item.total_price for item in returned_items)
        else:
            # Handle regular cancellations
            for item in order_items:
                if item.is_canceled:
                    refunded_amount += item.total_price

        # Calculate remaining amount and apply discounts
        remaining_amount = total_product_amount - refunded_amount
        amount_after_offers_coupon = remaining_amount

        if order.coupon_applied and order.coupon:
            coupon = order.coupon
            if coupon.coupon_type == 'percentage':
                discount_amount = (remaining_amount * coupon.discount_value) / 100
            else:
                discount_amount = min(coupon.discount_value, remaining_amount)
            amount_after_offers_coupon = remaining_amount - discount_amount

        # Create PDF
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        # Title and Header
        p.setFont("Helvetica-Bold", 24)
        p.drawCentredString(width / 2, height - 30, "Pagino Books")
        p.setFont("Helvetica-Bold", 14)
        p.drawCentredString(width / 2, height - 60, f"Invoice for Order-{order_id}")

        # Format address
        address_components = [
            order.delivery_address.street_name,
            order.delivery_address.building_no,
            f"Near {order.delivery_address.landmark}" if order.delivery_address.landmark else None,
            order.delivery_address.city,
            order.delivery_address.state,
            order.delivery_address.pincode
        ]
        formatted_address = ", ".join(filter(None, address_components))

        # Customer Info
        p.setFont("Helvetica", 12)
        y_pos = height - 80
        p.drawCentredString(width / 2, y_pos, f"Customer: {order.user.username} ({order.user.phone_number})")
        y_pos -= 25

        # Handle long addresses
        formatted_address = f"Shipping Address: {formatted_address}"
        for chunk in [formatted_address[i:i+60] for i in range(0, len(formatted_address), 60)]:
            p.drawCentredString(width / 2, y_pos, chunk)
            y_pos -= 20

        y_pos -= 20

        # Line Separator
        p.setLineWidth(1)
        p.line(50, y_pos, width - 50, y_pos)
        y_pos -= 30

        # Order Summary Header
        p.setFont("Helvetica-Bold", 12)
        p.drawString(100, y_pos, "Item Description")
        p.drawString(350, y_pos, "Quantity")
        p.drawString(450, y_pos, "Price")
        y_pos -= 20

        # List items
        p.setFont("Helvetica", 10)
        for item in order_items:
            # Skip returned items if partial return
            if return_request and not return_request.return_entire_order:
                if return_request.items.filter(order_item=item).exists():
                    continue
            # Calculate original and offer prices
            book = item.book
            original_price = book.base_price
            final_price = item.price_per_item
            
            product_offer = book.product_offer.filter(
                is_active=True,
                valid_from__lte=order.order_date,
                valid_to__gte=order.order_date
            ).first()
            
            category_offer = book.category.category_offers.filter(
                is_active=True,
                valid_from__lte=order.order_date,
                valid_to__gte=order.order_date
            ).first()

            # Draw item details
            # Book name (with word wrap if needed)
            book_name = book.book_name
            if len(book_name) > 30:
                book_name = book_name[:27] + "..."
            p.drawString(50, y_pos, book_name)
            
            # Original price
            p.drawRightString(340, y_pos, f"₹{original_price:,.2f}")
            
            p.setFont("Helvetica", 10)
            
            if product_offer or category_offer:
                offers_found = True
                # Book name with word wrap
                book_name = book.book_name
                if len(book_name) > 30:
                    book_name = book_name[:27] + "..."
                p.drawString(120, y_pos, f"Book: {book_name}")
                y_pos -= 20

                # Show product offer if exists
                if product_offer:
                    discount_info = ""
                    if product_offer.discount_type == 'percentage':
                        discount_info = f"{product_offer.discount_value}% off"
                    elif product_offer.discount_type == 'fixed':
                        discount_info = f"₹{product_offer.discount_value} off"
                    
                    p.drawString(140, y_pos, f"Product Offer: {product_offer.offer_name} - {discount_info}")
                    y_pos -= 20

                # Show category offer if exists
                if category_offer:
                    discount_info = ""
                    if category_offer.discount_type == 'percentage':
                        discount_info = f"{category_offer.discount_value}% off"
                    elif category_offer.discount_type == 'fixed':
                        discount_info = f"₹{category_offer.discount_value} off"
                    
                    p.drawString(140, y_pos, f"Category Offer: {category_offer.offer_name} - {discount_info}")
                    y_pos -= 20

                # Show savings for this item
                original_price = book.base_price
                final_price = item.price_per_item
                if original_price != final_price:
                    savings = (original_price - final_price) * item.quantity
                    p.drawString(140, y_pos, f"You saved: ₹{savings:,.2f} on this item")
                    y_pos -= 25

            else:
                p.drawString(120, y_pos, "No offers")
                y_pos -= 25

            # Final price and quantity
            p.drawRightString(530, y_pos, f"₹{final_price:,.2f}")
            p.drawRightString(380, y_pos, str(item.quantity))
            
            # Show savings
            if original_price != final_price:
                y_pos -= 15
                savings = (original_price - final_price) * item.quantity
                p.setFont("Helvetica", 9)
                p.drawString(70, y_pos, f"You saved: ₹{savings:,.2f}")
                if product_offer or category_offer:
                    applied_offer = product_offer or category_offer
                    p.drawString(200, y_pos, f"({applied_offer.offer_name})")
                p.setFont("Helvetica", 10)
            
            y_pos -= 25

        y_pos -= 10

        # Line Separator
        p.setLineWidth(1)
        p.line(50, y_pos, width - 50, y_pos)
        y_pos -= 30

        # Helper function for drawing info lines
        def draw_info_line(label, value, bold_value=False):
            nonlocal y_pos
            p.setFont("Helvetica-Bold", 12)
            p.drawString(100, y_pos, label)
            p.setFont("Helvetica-Bold" if bold_value else "Helvetica", 12)
            p.drawString(300, y_pos, value)
            y_pos -= 25

        # Payment Details
        draw_info_line("Payment Method:", str(order.payment_method))
        payment_status = "Completed" if order.payment_method in ['ONLINE', 'WALLET'] \
                        else "Paid" if order.order_status == "Delivered" \
                        else "Pending"
        draw_info_line("Payment Status:", payment_status)
        
         # Amount Details
        draw_info_line("Total Original Amount:", f"₹{sum(item.quantity * item.book.base_price for item in order_items):,.2f}")
        if order.offer_applied and order.offer:
            draw_info_line("Offer Discount:", f"₹{total_product_amount - sum(item.quantity * item.book.base_price for item in order_items):,.2f}")
        
        draw_info_line("Subtotal After Offers:", f"₹{total_product_amount:,.2f}")

        # Return/Refund Details
        if return_request:
            draw_info_line("Return Status:", return_request.status)
            draw_info_line("Refunded Amount:", f"₹{refunded_amount:,.2f}")
            draw_info_line("Final Amount:", f"₹{amount_after_offers_coupon:,.2f}", True)
            if return_request.admin_note:
                draw_info_line("Return Note:", return_request.admin_note)
        elif refunded_amount > 0:
            draw_info_line("Refunded Amount:", f"₹{refunded_amount:,.2f}")
            draw_info_line("Remaining Amount:", f"₹{remaining_amount:,.2f}", True)

        y_pos -= 10

        # Discount Section - Fixed to handle None values
        if order.coupon_applied and order.coupon:
            coupon_info = f"Code: {order.coupon.code} - {order.coupon.discount_value} {order.coupon.coupon_type}"
            draw_info_line("Coupon Applied:", coupon_info)
        else:
            draw_info_line("Coupon Status:", "No Coupon Applied")

        # Cancellation Details
        if order.is_canceled:
            y_pos -= 10
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

        # Save to file system
        pdf_name = f"invoice_{order_id}.pdf"
        media_path = os.path.join('media', 'invoices')
        pdf_path = os.path.join(media_path, pdf_name)

        os.makedirs(media_path, exist_ok=True)

        with open(pdf_path, 'wb') as f:
            f.write(buffer.getvalue())

        buffer.close()

        return JsonResponse({
            'status': 'success',
            'message': 'Invoice generated successfully!',
            'file_url': f'/media/invoices/{pdf_name}'
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

