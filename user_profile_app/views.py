from django.shortcuts import render,redirect,get_object_or_404
from user_profile_app.models import AddressTable,WalletTable,WalletTransaction
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
import re
from log_reg_app.models import UserTable
from django.contrib.auth import update_session_auth_hash
from order_detail_app.models import OrderDetails,OrderItem,CouponTable,CouponUsage
from django.db.models import Count
from django.db.models import Q
from django.urls import reverse
from paypalrestsdk import Payment
from django.conf import settings
from decimal import Decimal
import paypalrestsdk
from django.utils import timezone
# Create your views here.
#######################################################################################################################
def user_profile(request):
    profile = UserTable.objects.get(id=request.user.id)

    # updating the user information
    if request.method=="POST":
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        username = request.POST.get('username')
        email = request.POST.get('email')
        phone_number = request.POST.get('phone_number')
        gender = request.POST.get('gender')

        # updating the existing field
        profile.first_name = first_name
        profile.last_name = last_name
        profile.username = username
        profile.email = email
        profile.phone_number = phone_number
        profile.gender = gender

        profile.save()
        messages.success(request,"profile updated successfully")
        return redirect('user_profile')
    return render(request,'user_profile.html',{'profile':profile})

#######################################################################################################################

def user_address(request):
    addresses = AddressTable.objects.filter(user=request.user)
    return render(request,'user_address.html',{'addresses':addresses})

#######################################################################################################################

@login_required
def add_address(request):
    if request.method == "POST":
        address_name = request.POST.get('address_name')
        street_name= request.POST.get('street_name')
        building_no = request.POST.get('building_no')
        landmark = request.POST.get('landmark')
        city = request.POST.get('city')
        pincode = request.POST.get('pincode')
        address_phone = request.POST.get('address_phone')
        state = request.POST.get('state')

        is_valid = True
        try:
            #validation for address_name
            if not address_name:
                messages.error(request, "Full name is required")
                is_valid = False
            elif not all(char.isalpha() or char.isspace() for char in address_name):
                messages.error(request, "Name should only contain letters and spaces")
                is_valid = False
            elif len(address_name) < 3:
                messages.error(request, "Name should be at least 3 characters long")
                is_valid = False
            # validation for steet name

            if not street_name:
                messages.error(request, "Street address is required")
                is_valid = False
            elif len(street_name) < 5:
                messages.error(request, "Street address should be at least 5 characters long")
                is_valid = False
            elif not any(char.isalnum() for char in street_name):
                messages.error(request, "Street address should contain at least one alphanumeric character")
                is_valid = False

            # validation for building number
            if building_no and not any(char.isalnum() for char in building_no):
                messages.error(request, "Building/Apartment number should contain at least one alphanumeric character")
                is_valid = False
            
            # validation for city

            if not city:
                messages.error(request, "City is required")
                is_valid = False
            elif not all(char.isalpha() or char.isspace() for char in city):
                messages.error(request, "City should only contain letters and spaces")
                is_valid = False
            elif len(city) < 2:
                messages.error(request, "City name should be at least 2 characters long")
                is_valid = False

            # validation for state

            if not state:
                messages.error(request, "State is required")
                is_valid = False
            elif not all(char.isalpha() or char.isspace() for char in state):
                messages.error(request, "State should only contain letters and spaces")
                is_valid = False
            elif len(state) < 2:
                messages.error(request, "State name should be at least 2 characters long")
                is_valid = False

            # validation for picode

            if not pincode:
                messages.error(request, "Postal code is required")
                is_valid = False
            elif not re.match(r'^\d{6}$', pincode):  # Assuming 6-digit Indian pincode
                messages.error(request, "Please enter a valid 6-digit postal code")
                is_valid = False
            
            # validation for address_phone
            
            if not address_phone:
                messages.error(request, "Phone number is required")
                is_valid = False
            elif not re.match(r'^[6-9]\d{9}$', address_phone):
                messages.error(request, "Please enter a valid 10-digit Indian phone number")
                is_valid = False

            if is_valid:

                address = AddressTable(
                    user = request.user,
                    address_name= address_name,
                    street_name = street_name,
                    building_no = building_no,
                    landmark = landmark,
                    city = city,
                    pincode = pincode,
                    address_phone = address_phone,
                    state = state
                )
                address.save()
                return JsonResponse({
                    'status': 'success',
                    'message': 'Address added successfully!',
                    'redirect_url': reverse('user_address'),  # Ensure this URL exists
                })
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'An error occurred: {str(e)}'})
    return render(request,'add_address.html')

#######################################################################################################################

@login_required
def set_default_address(request, address_id):
    if request.method == 'POST':
        try:
            # First, set all addresses as non-default
            user_addresses = request.user.addresses.all()
            if user_addresses.count() > 1:
                user_addresses.update(is_default=False)
            # Set the selected address as default
                address = request.user.addresses.get(id=address_id)
                address.is_default = True
                address.save()
                
                return JsonResponse({'success': True})
            return JsonResponse({
                'success': False, 
                'error': 'Cannot change default status when only one address exists'
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

#######################################################################################################################
@login_required
def delete_address(request, address_id):
    try:
        address = AddressTable.objects.get(id=address_id, user=request.user)
        address.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

#######################################################################################################################
def edit_address(request,address_id):
    address = get_object_or_404(AddressTable, id=address_id, user=request.user)
    if request.method == 'POST':
        try:
            # Update address fields
            address.address_name = request.POST.get('address_name')
            address.street_name = request.POST.get('street_name')
            address.building_no = request.POST.get('building_no')
            address.landmark = request.POST.get('landmark')
            address.city = request.POST.get('city')
            address.pincode = request.POST.get('pincode')
            address.address_phone = request.POST.get('address_phone')
            address.state = request.POST.get('state')
            address.address_type = request.POST.get('address_type', 'home')
            
            # Save the updated address
            address.save()
            
            # Return success response
            return JsonResponse({
                'success': True,
                'message': 'Address updated successfully',
                'redirect_url': reverse('user_address')
            })
            
        except Exception as e:
            # Return error response
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
    return render(request, 'edit_address.html',{'address':address})
#######################################################################################################################
@login_required
def user_password_reset(request):
    if request.method == "POST":
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if not request.user.check_password(current_password):
            messages.error(request,"current password is incorrect")
            return redirect('user_password_reset')
        
        if new_password != confirm_password:
            messages.error(request,"New password and confirm password do not match")
            return redirect('user_password_reset')
        
        user = request.user
        request.user.set_password(new_password)
        user.save()

        update_session_auth_hash(request, user) 
        return JsonResponse({
            'status': 'success',
            'message': 'Your password has been successfully updated.',
            'redirect_url': reverse('user_profile')  # Ensure this URL exists
        })
    return render(request,'user_password_reset.html')

#######################################################################################################################
@login_required
def user_orders(request, order_id=None):
    order_stats = OrderDetails.objects.filter(user=request.user).aggregate(
        total_orders=Count('order_id'),
        delivered_orders=Count('order_id', filter=Q(order_status='Delivered')),
        in_progress_orders=Count('order_id', filter=Q(order_status='Pending')),
        shipped_orders=Count('order_id', filter=Q(order_status='Shipped')),
        canceled_orders=Count('order_id', filter=Q(order_status='Canceled'))
    )

    if order_id:
        # Combine select_related, prefetch_related, and annotate
        selected_order = get_object_or_404(
            OrderDetails.objects.select_related('user', 'address')  # Fetch user and address in one query
                                  .prefetch_related('orderitem_set__book__images')  # Prefetch related images
                                  .annotate(item_count=Count('orderitem')),  # Count related order items
            order_id=order_id,
            user=request.user
        )
        context = {
            'selected_order': selected_order,
            'order_stats': order_stats,
        }
    else:
        # Apply annotate to all user orders
        user_orders = OrderDetails.objects.filter(user=request.user).annotate(item_count=Count('orderitem')).order_by('-order_date')
        context = {
            'orders': user_orders,
            'order_stats': order_stats,
        }

    return render(request, 'user_orders.html', context)

#######################################################################################################################
def admin_single_item_cancel(request,order_id,order_item_id):
    if request.method == "POST":
        order_detail= get_object_or_404(OrderDetails, order_id=order_id)
        order_item = get_object_or_404(OrderItem, order=order_detail, id=order_item_id)

        order_item.is_canceled = True
        order_item.order_status = 'Canceled'
        order_item.save()

        #update the order status if all items are canceled
        if not OrderItem.objects.filter(order=order_detail, is_canceled=False).exists():
            order_detail.order_status = 'Canceled'
            order_detail.save()

        messages.success(request, f"Item has been canceled in Order {order_detail.order_id}.")
    return redirect('update_order',order_id=order_id)

########################################################################################################################

def user_coupon(request):

    current_time = timezone.now()
    # Fetch active coupons that are within the valid date range and still active
    available_coupons = CouponTable.objects.filter(
            is_active=True,
            valid_from__lte=current_time,
            valid_to__gte=current_time
        )
    used_coupons = CouponUsage.objects.filter(user=request.user).order_by('-used_at')   

    return render(request,'user_coupon.html',{'coupons':available_coupons,'used_coupons':used_coupons})

########################################################################################################################
paypalrestsdk.configure({
    "mode": settings.PAYPAL_MODE,  # Change to "live" for production
    "client_id": settings.PAYPAL_CLIENT_ID,
    "client_secret": settings.PAYPAL_CLIENT_SECRET
})

@login_required
def user_wallet(request):
        try:
            wallet = WalletTable.objects.get(user=request.user)
            
            # Retrieve transactions related to this wallet, ordered by transaction_time (latest first)
            transactions = wallet.transactions.order_by('-transaction_time')  # Use related_name defined in WalletTransaction
            
        except WalletTable.DoesNotExist:
            wallet = None
            transactions = []

        context = {
            'wallet': wallet,
            'transactions': transactions,
        }
        return render(request, 'user_wallet.html',context)

#########################################################################################################################
@login_required
def add_money_via_paypal(request):
    if request.method == "POST":
        try:
            amount = request.POST.get("amount")
            currency = request.POST.get("currency", "USD")
            
            # Validation
            try:
                amount = Decimal(amount)
                if amount <= Decimal('0'):
                    raise ValueError
            except (TypeError, ValueError):
                messages.error(request, "Please enter a valid amount.")
                return redirect("user_wallet")

            # if currency not in settings.ACCEPTED_CURRENCIES:
            #     messages.error(request, "Invalid currency selected.")
            #     return redirect("user_wallet")

            # Create PayPal payment
            payment = Payment({
                "intent": "sale",
                "payer": {
                    "payment_method": "paypal"
                },
                "redirect_urls": {
                    "return_url": request.build_absolute_uri(reverse('paypal_success')),
                    "cancel_url": request.build_absolute_uri(reverse('paypal_cancel'))
                },
                "transactions": [{
                    "amount": {
                        "total": str(amount),
                        "currency": currency
                    },
                    "description": f"Add {currency} {amount} to wallet"
                }]
            })

            if payment.create():
                request.session['paypal_payment_id'] = payment.id
                request.session['payment_amount'] = str(amount)
                request.session['payment_currency'] = currency
                
                # Find approval URL and redirect
                approval_url = next(
                    (link.href for link in payment.links if link.rel == "approval_url"),
                    None
                )
                if approval_url:
                    return redirect(approval_url)
            
            messages.error(request, "Failed to create PayPal payment. Please try again.")
            
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
        
        return redirect("user_wallet")

    return redirect("user_wallet")

###################################################################################################################

@login_required
def paypal_success(request):
    try:
        payment_id = request.GET.get("paymentId")
        payer_id = request.GET.get("PayerID")
        
        # Security verification
        stored_payment_id = request.session.get('paypal_payment_id')
        if not payment_id or payment_id != stored_payment_id:
            messages.error(request, "Invalid payment session.")
            return redirect("user_wallet")

        payment = Payment.find(payment_id)
        print(payment)
        if payment.execute({"payer_id": payer_id}):
            amount = Decimal(request.session.get('payment_amount'))
            currency = request.session.get('payment_currency')
            
            try:
                # Get or create the wallet for the user
                wallet, created = WalletTable.objects.get_or_create(user=request.user)
                
                # Update the wallet's available balance
                wallet.available_balance += amount
                wallet.save()

                # Log the transaction
                WalletTransaction.objects.create(
                    wallet=wallet,
                    transaction_type="add",
                    transaction_amount=amount,
                    description=f"PayPal Payment ({payment_id})"
                )
                
                # Clear session data
                for key in ['paypal_payment_id', 'payment_amount', 'payment_currency']:
                    request.session.pop(key, None)
                
                # Notify the user
                messages.success(
                    request, 
                    f"Successfully added {currency} {amount:,.2f} to your wallet!"
                )
            except Exception as e:
                messages.error(request, f"Failed to update wallet: {str(e)}")
            except Exception as e:
                messages.error(request, f"Failed to update wallet: {str(e)}")
        else:
            messages.error(request, "Payment execution failed. Please try again.")
            
    except Exception as e:
        messages.error(request, f"Payment processing error: {str(e)}")
    
    return redirect("user_wallet")

#############################################################################################################################

@login_required
def paypal_cancel(request):
    # Clear session data
    for key in ['paypal_payment_id', 'payment_amount', 'payment_currency']:
        request.session.pop(key, None)
    
    messages.warning(request, "Payment was cancelled.")
    return redirect("user_wallet")

##############################################################################################################################