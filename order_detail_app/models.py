from django.db import models
import random
import string
from log_reg_app.models import UserTable
from user_profile_app.models import AddressTable
from adminside_app.models import BookTable,CategoryTable

import uuid 

def generate_order_id():
    # Generate a unique order ID
    while True:
        order_id = ''.join(random.choices(string.ascii_uppercase + string.ascii_lowercase + string.digits, k=10))
        if not OrderDetails.objects.filter(order_id=order_id).exists():
            return order_id

# Create your models here.

class CouponTable(models.Model):
    code = models.CharField(max_length=20, unique=True)  # Unique code for the coupon
    coupon_type = models.CharField(
        max_length=20,
        choices=[('percentage', 'Percentage'), ('fixed', 'Vat Amount')],
        default='percentage'
    )
    discount_value = models.DecimalField(max_digits=10, decimal_places=2,null=True, blank=True)
    min_purchase_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_uses = models.PositiveIntegerField(null=True, blank=True)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Coupon {self.code} ({self.coupon_type}: {self.discount_value})"



class OfferTable(models.Model):
    offer_name = models.CharField(max_length=50)
    OFFER_TYPES = [
        ('category', 'Category Offer'),
        ('product', 'Single Product Offer'),
        ('special', 'Special Day Offer'),
        ('seasonal', 'Seasonal Offer'),
    ]
    DISCOUNT_TYPES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
        ('bogo', 'Buy One Get One'),
        ('bundle', 'Bundle Discount'),
    ]
    offer_type = models.CharField(max_length=20, choices=OFFER_TYPES)
    product = models.ForeignKey(BookTable, on_delete=models.CASCADE, null=True,blank=True)
    category = models.ForeignKey(CategoryTable, on_delete=models.CASCADE, null=True, blank=True)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPES,null=True,blank=True)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2,null=True,blank=True)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Offer {self.name} ({self.discount_percentage}% or ₹{self.discount_amount})"
    



class OrderDetails(models.Model):
    order_id = models.CharField(max_length =10, primary_key=True)
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
                                             ('Out of delivery','Out of delivery'),
                                             ('Delivered', 'Delivered'),
                                             ('Canceled','Canceled')], 
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
    razorpay_order_id = models.CharField(max_length=100, null=True, blank=True)
    razorpay_payment_id = models.CharField(max_length=100, null=True, blank=True)
    
    def __str__(self):
        return f"Order {self.order_id} by {self.user.username}"
    

class OrderItem(models.Model):
    order = models.ForeignKey(OrderDetails, on_delete=models.CASCADE, to_field='order_id',db_column='order_id', null=True)
    book = models.ForeignKey(BookTable,on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    price_per_item = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_canceled = models.BooleanField(default=False)  
    order_status = models.CharField(max_length=20, 
                                    choices=[('Pending', 'Pending'),
                                             ('Shipped', 'Shipped'),
                                             ('Delivered', 'Delivered'),
                                             ('Out of delivery','Out of delivery'),
                                             ('Canceled','Canceled')], 
                                             default='Pending')
    def __str__(self):
        return f"{self.quantity} x {self.product.name} in Order {self.order.order_id}"