from django.shortcuts import render, redirect
from log_reg_app.models import UserTable
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.urls import reverse
import random
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control,never_cache
import re
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from allauth.socialaccount.views import SignupView
from django.shortcuts import redirect
from django.contrib.auth import login
from django.views import View
from django.shortcuts import redirect
from django.contrib.auth import login
from allauth.socialaccount.models import SocialApp
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.helpers import complete_social_login
from allauth.socialaccount.models import SocialLogin
from order_detail_app.models import OfferTable
from user_side_app.models import CartTable,WhishlistTable
from django.db.models import F

class CustomGoogleCallbackView(View):
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('homepage_after_login')

        try:
            # Initialize the adapter
            adapter = GoogleOAuth2Adapter(request)

            # Complete the login process using allauth's helper method
            login_data = complete_social_login(request, adapter)

            if login_data:
                if login_data.user.is_superuser:
                    messages.error(request, "Superusers are not allowed to log in using Google authentication.")
                    return redirect('user_login')
                # If it's an existing user, log them in and redirect to the homepage
                if login_data.is_existing:
                    login(request, login_data.user)
                    return redirect('homepage_after_login')
                else:
                    # For new users, save the data and log them in
                    login_data.lookup()
                    login_data.save(request, connect=True)
                    login(request, login_data.user)
                    return redirect('homepage_after_login')

            return redirect('user_login')  # Redirect to login if login data is not found

        except Exception as e:
            return redirect('user_login')  # Adjust this URL to the correct login page



###############################################################################################################
@never_cache
def homepage_before_login(request):
    active_offers = OfferTable.objects.filter(is_active=True)
    return render(request,'homepage_before_login.html',{'active_offers':active_offers})

######################################################################################################################

def user_signup(request):

    if request.method == "POST":
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        phone_number = request.POST.get('phone_number')
        gender = request.POST.get('gender')
        
        try:
            #validate require fields
            if not first_name.isalpha():
                messages.error(request, "First name should contain only alphabets.")
                return render(request, 'user_signup.html')
            
            if not last_name.isalpha():
                messages.error(request, "Last name should contain only alphabets.")
                return render(request, 'user_signup.html')

            # validate the username  field
            if len(username) < 3 or len(username)>30:
                messages.error(request,"username must be between 3 and 30 characters.")
                return render(request,'user_signup.html')
            
            if not username.isalnum() and "_" not in username and "-" not in username:
                messages.error(request,"username can only contain letters, numbers, underscores,and hyphens.")
                return render(request,'user_signup.html')
            
            if username.lower() in ['admin','user']:
                messages.error(request,"This username is not allowed")
                return render(request,'user_signup.html')
            
            if UserTable.objects.filter(username=username).exists(): # user name is already exist or not
                messages.error(request,"Username is already taken")
                return render(request,'user_signup.html')
            if len(password) < 8:
                messages.error(request, "Password must be at least 8 characters.")
                return render(request, 'user_signup.html')
            
            if not any(c.isupper() for c in password):
                messages.error(request, "Password must contain uppercase letters.")
                return render(request, 'user_signup.html')
                
            if not any(c.islower() for c in password):
                messages.error(request, "Password must contain lowercase letters.")
                return render(request, 'user_signup.html')
                
            if not any(c.isdigit() for c in password):
                messages.error(request, "Password must contain numbers.")
                return render(request, 'user_signup.html')
                
            if not any(c in "!@#$%^&*" for c in password):
                messages.error(request, "Password must contain special characters (!@#$%^&*).")
                return render(request, 'user_signup.html')

            if password != confirm_password:
                messages.error(request, "Passwords do not match")
                return render(request, 'user_signup.html')
            
            # mail validation
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                messages.error(request, "Invalid email format.")
                return render(request, 'user_signup.html')
        
            if UserTable.objects.filter(email=email).exists():  # eamil id is already exist or not
                messages.error(request, "Email id is already taken")
                return render(request,'user_signup.html')
            
            if not re.match(r'^[6-9]\d{9}$',phone_number):
                messages.error(request,'Invalid phone number')
                return render(request,'user_signup.html')
            
            if UserTable.objects.filter(phone_number=phone_number).exists():
                messages.error(request,"This number is already taken")
                return render(request,'user_signup.html')
            
            
            if not all([first_name,last_name,username,email,password,phone_number,gender]): # checking all the fields are entered
                messages.error(request, "All fields are required")
                return render(request,'user_signup.html')

            

            user = UserTable(
                first_name=first_name,
                last_name=last_name,
                username=username,
                email = email,
                phone_number = phone_number,
                gender = gender
            )
            user.set_password(password) # hash password
            user.save()

            otp = random.randint(100000, 999999)  # Generate a 6-digit OTP
            # Store OTP and email in session
            request.session['otp'] = otp
            request.session['otp_timestamp'] = timezone.now().isoformat()
            request.session['email'] = email  # Store email in session

            # Send OTP via email
            try:
                send_mail(
                    'Your OTP for Account Verification',
                    f'Your OTP code is {otp}. It will expire in 90 seconds.',
                    settings.EMAIL_HOST_USER, 
                    [email], 
                    fail_silently=False,
                )
                messages.success(request, 'OTP has been sent to your email. Please check and verify.')
                return redirect('verify_otp')
            except Exception as e:
                messages.error(request, f'Error sending OTP: {str(e)}')
                return render(request, 'user_signup.html')
        
        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')
            return render(request, 'user_signup.html')

    return render(request,'user_signup.html')

############################################################################################

def user_login(request):

    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username = username, password = password)
        if user is not None and not user.is_superuser:
            # Check if the user is active
            if user.is_active:
                login(request, user)
                return redirect('homepage_after_login')
            else:
                messages.error(request, "Your account is inactive. Please contact support.")
                return render(request,'user_login.html')
    
        else:
            messages.error(request,"username or password is invalid")
        return render(request,'user_login.html')
    
    if request.method == "GET":
        if request.user.is_authenticated:
            return redirect('homepage_after_login')
    return render(request,'user_login.html')

########################################################################################################

def user_logout(request):
    logout(request)
    request.session.flush()
    messages.success(request, "You have been logged out successfully.")
    return redirect('homepage_before_login')

######################################################################################################
def admin_login(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request,username=username,password = password)
        if user is not None and user.is_superuser:
            login(request, user)
            messages.success(request,f"{username}logined successfully." )
            return redirect(reverse('admin_dashboard'))
        else:
            if user is not None:
                messages.error(request,"You don't have admin privileges")
            return render(request,'admin_login.html')
        
    if request.method == "GET":
        if request.user.is_authenticated:
            if request.user.is_superuser:
                return redirect('admin_dashboard')
            else:
                messages.error(request,"you dont have admin privileges")
                return render(request,'admin_login.html')
            
    return render(request,'admin_login.html')

##############################################################################################################

def admin_logout(request):
    logout(request)
    request.session.flush()
    return redirect('admin_login')

##############################################################################################################
@never_cache
@login_required(login_url='user_login')
def homepage_after_login(request):
    return render(request,'homepage_after_login.html')

##################################################################################################################
def forgot_password(request):  
    if request.method == "POST":
        email = request.POST.get('email')
        try:
            # fetch user from model
            user = UserTable.objects.get(email = email)
            otp = random.randint(100000,999999)     # Generate 6 digit OTP

            # storing otp and timestamp in session for security
            request.session['otp'] = otp
            request.session['otp_timestamp'] = timezone.now().isoformat()
            request.session['email'] = email  # store email in session
            request.session['otp_for_reset'] = True # flag to indicate password reset flow 

            # send otp via mail
            try: 
                send_mail(
                    'Your OneTimePassword for password Reset',
                    f'Your OTP code is {otp}.It will expire in 90 seconds.',
                    'jubink76@gmail.com',
                    [email],
                    fail_silently=False,
                )
                messages.success(request,'OTP has been sent to your registered email id , Please check and verify')
            except Exception as e:
                messages.error(request, 'There was an error sending the email:{}'.format(e))
            return redirect('verify_otp')
        except UserTable.DoesNotExist:
            messages.error(request,'Email does not exist')

    return render(request,'forgot_password.html')

###################################################################################################################

def verify_otp(request):
    if request.method == "POST":
        entered_otp = (
            request.POST.get('otp1') +
            request.POST.get('otp2') +
            request.POST.get('otp3') +
            request.POST.get('otp4') +
            request.POST.get('otp5') +
            request.POST.get('otp6')
        )
        stored_otp = request.session.get('otp')
        otp_timestamp = request.session.get('otp_timestamp')
        otp_for_reset = request.session.get('otp_for_reset', False)

        # Ensure otp_timestamp is a datetime object
        if otp_timestamp is not None:
            # Convert timestamp string to datetime object if needed
            otp_timestamp = timezone.datetime.fromisoformat(otp_timestamp)

            # Check if the OTP is correct and not expired (90 seconds)
            if stored_otp and timezone.now() < otp_timestamp + timedelta(seconds=90):
                if str(entered_otp) == str(stored_otp):
                    # OTP is valid
                    messages.success(request, 'OTP verified successfully')
                    if otp_for_reset:
                        # clear the reset flag and redirect to set password page
                        del request.session['otp_for_reset']
                        return redirect('set_password')
                    else:
                        # clear otp data from session for signup 
                        del request.session['otp']
                        del request.session['otp_timestamp']
                        return redirect('user_login')
                else:
                    messages.error(request, 'Invalid OTP')
                    
            else:
                messages.error(request, 'OTP has expired.')
                
        else:
            messages.error(request, 'OTP timestamp not found.')

    return render(request, 'verify_otp.html')

####################################################################################################################


def set_password(request):
    if request.method == "POST":
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']

        email = request.session.get('email') # get the email from the session 
        if email: # checking if email is in session
            try:
                user = UserTable.objects.get(email = email)
                if password == confirm_password:
                    user.set_password(password)
                    user.save()
                    messages.success(request,'password reset successfully')
                    return redirect('user_login')
                else:
                    messages.error(request,'passwords do not match')
            except UserTable.DoesNotExist:
                messages.error(request,'User does not exist.')
        else:
            messages.error(request,'email mot found')
    return render(request,'set_password.html')

######################################################################################################

def resend_otp(request):
    if request.method == "POST":
        email = request.session.get('email')  # Retrieve email from session
        if email:
            try:
                user = UserTable.objects.get(email=email)
                otp = random.randint(100000, 999999)  # Generate a new OTP
                request.session['otp'] = otp
                request.session['otp_timestamp'] = timezone.now().isoformat()
                
                # Send OTP via email
                send_mail(
                    'Your One-Time Password',
                    f'Your OTP code is {otp}. It will expire in 90 seconds.',
                    'your_email@example.com',
                    [email],
                    fail_silently=False,
                )
                return JsonResponse({'success': True})
            except UserTable.DoesNotExist:
                messages.error(request, 'Email does not exist')
                return JsonResponse({'success': False, 'message': 'Email does not exist'})
        else:
            return JsonResponse({'success': False, 'message': 'No email in session'})

    return JsonResponse({'success': False, 'message': 'Invalid request'})

#############################################################################################################################
