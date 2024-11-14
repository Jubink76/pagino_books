from django.db import models
import random
import string
from log_reg_app.models import UserTable
from user_profile_app.models import AddressTable
from adminside_app.models import BookTable
import uuid 

# creating random alpha-numeric order id 
def generate_order_id():
    return ''.join(random.choices(string.ascii_uppercase + string.ascii_lowercase + string.digits, k=10))

# Create your models here.
def generate_coupon_code():
    return str(uuid.uuid4()).replace('-', '').upper()[:10] 

class CouponTable(models.Model):
    code = models.CharField(max_length=20, default=generate_coupon_code, unique=True)  # Unique code for the coupon
    coupon_type = models.CharField(
        max_length=20,
        choices=[('flat', 'Flat'), ('percentage', 'Percentage')]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Coupon {self.code} ({self.discount_percentage}% or ₹{self.discount_amount})"



class OfferTable(models.Model):
    name = models.CharField(max_length=50)
    offer_type = models.CharField(
        max_length=20,
        choices=[('flat', 'Flat'), ('percentage', 'Percentage')]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Offer {self.name} ({self.discount_percentage}% or ₹{self.discount_amount})"
    



class OrderDetails(models.Model):
    order_id = models.CharField(max_length =10, unique=True,default=generate_order_id,editable=False)
    user = models.ForeignKey(UserTable,on_delete=models.CASCADE,null=True,blank=True)
    address = models.ForeignKey(AddressTable, on_delete=models.SET_NULL, null=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20,
                                      choices=[('COD', 'Cash on Delivery'),
                                               ('ONLINE', 'Online Payment'),
                                               ('WALLET', 'Wallet Payment')])
    order_status = models.CharField(max_length=20, 
                                    choices=[('Pending', 'Pending'),
                                             ('Shipped', 'Shipped'),
                                             ('Delivered', 'Delivered')], 
                                             default='Pending')
    order_date = models.DateTimeField(auto_now_add=True)
    coupon_applied = models.BooleanField(default = False)
    coupon = models.ForeignKey(CouponTable, on_delete=models.SET_NULL, null=True, blank=True)
    offer_applied = models.BooleanField(default = False)
    offer = models.ForeignKey(OfferTable, on_delete=models.SET_NULL, null=True, blank=True)
    is_canceled = models.BooleanField(default=False)
    cancel_description = models.TextField(blank=True, null=True)
    cancel_date = models.DateTimeField(blank=True, null=True)
    is_refund = models.BooleanField(default=False)
    refund_date = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"Order {self.order_id} by {self.user.username}"
    

class OrderItem(models.Model):
    order = models.ForeignKey(OrderDetails, related_name='items', on_delete=models.CASCADE)
    book = models.ForeignKey(BookTable,on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.PositiveIntegerField()
    price_per_item = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)  # price_per_item * quantity

    def __str__(self):
        return f"{self.quantity} x {self.product.name} in Order {self.order.order_id}"