from django.shortcuts import render,redirect,get_object_or_404
from user_profile_app.models import AddressTable,WalletTable,WalletTransaction
from adminside_app.models import BookTable
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
import re
from log_reg_app.models import UserTable
from django.contrib.auth import update_session_auth_hash
from order_detail_app.models import OrderDetails,OrderItem,CouponTable,CouponUsage,ReturnRequest,ReviewTable
from django.db.models import Count
from django.db.models import Q,F
from django.urls import reverse
from paypalrestsdk import Payment
from django.conf import settings
from decimal import Decimal
import paypalrestsdk
from django.utils import timezone
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Prefetch
# Create your views here.
#######################################################################################################################

def user_profile(request):
    if request.method == "POST":
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        username = request.POST.get('username')
        email = request.POST.get('email')
        phone_number = request.POST.get('phone_number')
        gender = request.POST.get('gender')

        is_valid = True
        errors = {}

        # First name validation
        if not first_name:
            errors['first_name'] = "First name is required"
            is_valid = False
        elif not all(char.isalpha() or char.isspace() for char in first_name):
            errors['first_name'] = "First name should only contain letters and spaces"
            is_valid = False
        elif len(first_name) < 2:
            errors['first_name'] = "First name should be at least 2 characters"
            is_valid = False

        # Last name validation
        if not last_name:
            errors['last_name'] = "Last name is required"
            is_valid = False
        elif not all(char.isalpha() or char.isspace() for char in last_name):
            errors['last_name'] = "Last name should only contain letters and spaces"
            is_valid = False
        elif len(last_name) < 2:
            errors['last_name'] = "Last name should be at least 2 characters" 
            is_valid = False

        # Username validation
        if not username:
            errors['username'] = "Username is required"
            is_valid = False
        elif not re.match(r'^[a-zA-Z0-9_]+$', username):
            errors['username'] = "Username should only contain letters, numbers and underscores"
            is_valid = False
        elif UserTable.objects.exclude(id=request.user.id).filter(username=username).exists():
            errors['username'] = "This username is already taken"
            is_valid = False

        # Email validation
        if not email:
            errors['email'] = "Email is required"
            is_valid = False
        elif not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
            errors['email'] = "Please enter a valid email address"
            is_valid = False
        elif UserTable.objects.exclude(id=request.user.id).filter(email=email).exists():
            errors['email'] = "This email is already registered"
            is_valid = False

        # Phone validation
        if phone_number and not re.match(r'^[6-9]\d{9}$', phone_number):
            errors['phone_number'] = "Please enter a valid 10-digit phone number"
            is_valid = False

        if is_valid:
            try:
                profile = UserTable.objects.get(id=request.user.id)
                profile.first_name = first_name
                profile.last_name = last_name
                profile.username = username
                profile.email = email
                profile.phone_number = phone_number
                profile.gender = gender
                profile.save()
                
                return JsonResponse({
                    'status': 'success',
                    'message': 'Profile updated successfully!',
                    'redirect_url': reverse('user_profile')
                })
            except Exception as e:
                return JsonResponse({
                    'status': 'error', 
                    'message': f'An error occurred: {str(e)}'
                })
        else:
            return JsonResponse({
                'status': 'error',
                'errors': errors
            })

    profile = UserTable.objects.get(id=request.user.id)
    return render(request, 'user_profile.html', {'profile': profile})

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

        errors = {}
        if not current_password:
            errors['current_password'] = 'Current password is required'
        elif not request.user.check_password(current_password):
            errors['current_password'] = 'Current password is incorrect'

        if not new_password:
            errors['new_password'] = 'New password is required'
        elif len(new_password) < 8:
            errors['new_password'] = 'Password must be at least 8 characters'
        elif not any(c.isupper() for c in new_password):
            errors['new_password'] = 'Password must contain uppercase letters'
        elif not any(c.islower() for c in new_password):
            errors['new_password'] = 'Password must contain lowercase letters'
        elif not any(c.isdigit() for c in new_password):
            errors['new_password'] = 'Password must contain numbers'

        if new_password != confirm_password:
            errors['confirm_password'] = 'Passwords do not match'

        if errors:
            return JsonResponse({
                'status': 'error',
                'errors': errors
            })

        try:
            user = request.user
            user.set_password(new_password)
            user.save()
            update_session_auth_hash(request, user)
            return JsonResponse({
                'status': 'success',
                'message': 'Your password has been successfully updated.',
                'redirect_url': reverse('user_profile')
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })

    return render(request, 'user_password_reset.html')

#######################################################################################################################
@login_required
def user_orders(request):

    try:
        # Calculate order statistics
        order_stats = OrderDetails.objects.filter(user=request.user).aggregate(
            total_orders=Count('order_id'),
            delivered_orders=Count('order_id', filter=Q(order_status='Delivered')),
            pending_orders=Count('order_id', filter=Q(order_status='Pending')),
            in_progress_orders=Count('order_id', filter=Q(order_status='Ordered')),
            shipped_orders=Count('order_id', filter=Q(order_status='Shipped')),
            canceled_orders=Count('order_id', filter=Q(order_status='Canceled'))
        )
        print(order_stats.items)
        # Determine which orders can have an invoice button
        orders_with_button = OrderDetails.objects.filter(
            Q(payment_method__in=['ONLINE', 'WALLET']) | Q(order_status='Delivered'),
            user=request.user
        ).values_list('order_id', flat=True)

        # Get user's reviews to mark reviewed items
        user_reviews = ReviewTable.objects.filter(user=request.user).values_list('order_id', 'book_id')
        reviewed_items = set((order_id, book_id) for order_id, book_id in user_reviews)

        # Fetch and prefetch orders with related data
        order_list = OrderDetails.objects.filter(user=request.user)\
            .prefetch_related(
                Prefetch(
                    'returnrequest_set',
                    queryset=ReturnRequest.objects.select_related('order')
                                                .order_by('-created_at')
                                                .prefetch_related('items__order_item__book')
                )
            )\
            .prefetch_related('orderitem_set__book__images')\
            .annotate(item_count=Count('orderitem'))\
            .order_by('-order_date')

        # Add review status to order items
        for order in order_list:
            for item in order.orderitem_set.all():
                item.is_reviewed = (order.order_id, item.book.id) in reviewed_items

        # Paginate the orders
        paginator = Paginator(order_list, 5)  # Show 5 orders per page
        page_number = request.GET.get('page')
        
        try:
            orders = paginator.page(page_number)
        except PageNotAnInteger:
            orders = paginator.page(1)
        except EmptyPage:
            orders = paginator.page(paginator.num_pages)

        context = {
            'orders': orders,
            'order_stats': order_stats,
            'orders_with_button': orders_with_button,
            'reviewed_items': reviewed_items,
        }

        return render(request, 'user_orders.html', context)
    
    except Exception as e:
        # Log the error for debugging
        print(f"Error in user_orders_list view: {str(e)}")
        messages.error(request, "An error occurred while loading your orders. Please try again.")
        return redirect('homepage_after_login')
    
########################################################################################################################
@login_required
def user_order_detail(request,order_id):
    try:
        # Fetch the specific order with all related data
        selected_order = get_object_or_404(
            OrderDetails.objects.select_related('user', 'address')
                             .prefetch_related('orderitem_set__book__images')
                             .prefetch_related('returnrequest_set')
                             .prefetch_related('returnrequest_set__items__order_item__book')
                             .annotate(item_count=Count('orderitem')),
            order_id=order_id,
            user=request.user
        )

        # Check if the user wants to write a review
        show_review_form = False
        selected_book = None

        if request.method == "POST" and 'review_order' in request.POST:
            book_id = request.POST.get('book_id')
            selected_book = get_object_or_404(OrderItem.objects.select_related('book'), id=book_id).book
            show_review_form = True

        # Get user's reviews to mark reviewed items
        user_reviews = ReviewTable.objects.filter(user=request.user).values_list('order_id', 'book_id')
        reviewed_items = set((order_id, book_id) for order_id, book_id in user_reviews)

        # Mark items as reviewed
        for item in selected_order.orderitem_set.all():
            item.is_reviewed = (selected_order.order_id, item.book.id) in reviewed_items

        context = {
            'selected_order': selected_order,
            'selected_book': selected_book,
            'show_review_form': show_review_form,
            'is_single_item_order': selected_order.item_count == 1,
        }

        return render(request, 'user_order_detail.html', context)
    
    except Exception as e:
        # Log the error for debugging
        print(f"Error in user_order_detail view: {str(e)}")
        messages.error(request, "An error occurred while loading your order details. Please try again.")
        return redirect('user_orders')
    

########################################################################################################################

def user_coupon(request):
    current_time = timezone.now()
    
    # Get all active coupons within valid date range
    available_coupons = CouponTable.objects.filter(
        is_active=True,
        valid_from__lte=current_time,
        valid_to__gte=current_time
    )
    
    # Get the user's used coupons
    used_coupons = CouponUsage.objects.filter(
        user=request.user, 
        is_used=True
    ).order_by('-used_at')
    
    # Get the coupon IDs that the user has already used
    used_coupon_ids = used_coupons.values_list('coupon_id', flat=True)
    
    available_coupons = available_coupons.exclude(
        id__in=used_coupon_ids
    ).annotate(
        total_uses=Count('couponusage'),
        user_uses=Count(
            'couponusage',
            filter=Q(couponusage__user=request.user)
        )
    ).filter(
        Q(max_uses__isnull=True) | Q(total_uses__lt=F('max_uses')),
        user_uses__lt=F('max_uses_per_user')
    )

    return render(
        request,
        'user_coupon.html',
        {
            'coupons': available_coupons,
            'used_coupons': used_coupons
        }
    )

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