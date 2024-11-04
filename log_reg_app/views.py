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

# Create your views here.


###############################################################################################################
def homepage_before_login(request):
    return render(request,'homepage_before_login.html')

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
            if UserTable.objects.filter(username=username).exists(): # user name is already exist or not
                messages.error(request,"Username is already taken")
                return render(request,'user_signup.html')
        

            if UserTable.objects.filter(email=email).exists():  # eamil id is already exist or not
                messages.error(request, "Email id is already taken")
                return render(request,'user_signup.html')
            
            if not all([first_name,last_name,username,email,password,phone_number,gender]): # checking all the fields are entered
                messages.error(request, "All fields are required")
                #return render(request,'user_signup.html')
            

            if password != confirm_password: # rechecking the password correct or not
                messages.error(request,"Invalid password")
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
            send_mail(
                'Your OTP for Account Verification',
                f'Your OTP code is {otp}. It will expire in 90 seconds.',
                'your_email@example.com',  # Replace with your email
                [email],
                fail_silently=False,
            )

            messages.success(request, 'OTP has been sent to your email. Please check and verify.')
            return redirect('verify_otp') 
        
        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')
            return render(request, 'user_signup.html')

    return render(request,'user_signup.html')

############################################################################################
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def user_login(request):
    
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username = username, password = password)
        if user is not None:
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

###################################################       #####################################################
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@never_cache
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
                print("Redirecting to admin dashboard for an already authenticated superuser.")
                return redirect(reverse('admin_dashboard'))
            else:
                messages.error(request,"you dont have admin privileges")
                return render(request,'admin_login.html')
    return render(request,'admin_login.html')

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@never_cache
def admin_logout(request):
    logout(request)
    request.session.flush()
    return redirect('admin_login')

@login_required(login_url='user_login')
@never_cache
def homepage_after_login(request):
    return render(request,'homepage_after_login.html')

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
                print(f'Error sending email: {e}')
            return redirect('verify_otp')
        except UserTable.DoesNotExist:
            messages.error(request,'Email does not exist')

    return render(request,'forgot_password.html')

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

        # Ensure otp_timestamp is a datetime object
        if otp_timestamp is not None:
            # Convert timestamp string to datetime object if needed
            otp_timestamp = timezone.datetime.fromisoformat(otp_timestamp)

            # Check if the OTP is correct and not expired (90 seconds)
            if stored_otp and timezone.now() < otp_timestamp + timedelta(seconds=90):
                if str(entered_otp) == str(stored_otp):
                    # OTP is valid
                    messages.success(request, 'OTP verified successfully')
                    return redirect('user_login')
                else:
                    messages.error(request, 'Invalid OTP')
                    
            else:
                messages.error(request, 'OTP has expired.')
                
        else:
            messages.error(request, 'OTP timestamp not found.')

    return render(request, 'verify_otp.html')


@never_cache
def set_password(request):
    if request.method == "POST":
        password1 = request.POST['password1']
        password2 = request.POST['password2']

        email = request.session.get('email') # get the email from the session 
        if email: # checking if email is in session
            try:
                user = UserTable.objects.get(email = email)
                if password1 == password2:
                    user.set_password(password1)
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