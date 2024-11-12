from django.shortcuts import render

# Create your views here.
#######################################################################################################################
def user_profile(request):
    return render(request,'user_profile.html')

#######################################################################################################################

def user_address(request):
    return render(request,'user_address.html')

#######################################################################################################################

def add_address(request):
    return render(request,'add_address.html')

#######################################################################################################################

def user_orders(request):
    return render(request,'user_orders.html')

#######################################################################################################################

def user_password_reset(request):
    return render(request,'user_password_reset.html')

#######################################################################################################################
