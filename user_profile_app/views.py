from django.shortcuts import render,redirect,get_object_or_404
from user_profile_app.models import AddressTable
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
import re
from log_reg_app.models import UserTable
from django.contrib.auth import update_session_auth_hash
from order_detail_app.models import OrderDetails,OrderItem
from django.db.models import Count
from django.db.models import Q
from django.urls import reverse
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
        # Ensure only valid related fields are used
        selected_order = get_object_or_404(
            OrderDetails.objects.select_related('user', 'address')  # Adjust this
                                .prefetch_related('orderitem_set__book__images'),
            order_id=order_id,
            user=request.user
        )
        context = {
            'selected_order': selected_order,
            'order_stats': order_stats,
        }
    else:
        user_orders = OrderDetails.objects.filter(
            user=request.user
        ).order_by('-order_date')

        context = {
            'orders': user_orders,
            'order_stats': order_stats,
        }

    return render(request, 'user_orders.html', context)

#######################################################################################################################


########################################################################################################################

