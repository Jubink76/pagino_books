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
    code = models.CharField(max_length=20, unique=True,null=True, blank=True)  # Unique code for the coupon
    coupon_type = models.CharField(
        max_length=20,
        choices=[('percentage', 'Percentage'), ('fixed', 'Vat Amount')],
        default='percentage'
    )
    discount_value = models.DecimalField(max_digits=10, decimal_places=2,null=True, blank=True)
    min_purchase_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_uses = models.PositiveIntegerField(null=True, blank=True)
    max_uses_per_user = models.PositiveIntegerField(default=1)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Coupon {self.code} ({self.coupon_type}: {self.discount_value})"
    
class CouponUsage(models.Model):
    user = models.ForeignKey('log_reg_app.UserTable', on_delete=models.CASCADE) 
    coupon = models.ForeignKey(CouponTable, on_delete=models.CASCADE)  
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)  
    used_at = models.DateTimeField(auto_now_add=True) 
    is_used = models.BooleanField(default=False)

    class Meta:
        ordering = ['-used_at']

    def __str__(self):
        return f"{self.user.username} used {self.coupon.code} on {self.used_at}"



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
    product = models.ForeignKey('adminside_app.BookTable', on_delete=models.CASCADE, null=True,blank=True,related_name='product_offer')
    category = models.ForeignKey('adminside_app.CategoryTable', on_delete=models.CASCADE, null=True, blank=True,related_name='category_offers')
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPES,null=True,blank=True)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2,null=True,blank=True)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Offer {self.offer_name}"
    


class OrderDetails(models.Model):
    order_id = models.CharField(max_length =10, primary_key=True)
    user = models.ForeignKey(UserTable,on_delete=models.CASCADE,null=True,blank=True)
    address = models.ForeignKey(AddressTable, on_delete=models.SET_NULL, null=True)
    delivery_address = models.ForeignKey('order_detail_app.OrderAddress', on_delete=models.PROTECT,null=True,blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20,
                                      choices=[('COD', 'Cash on Delivery'),
                                               ('ONLINE', 'Online Payment'),
                                               ('WALLET', 'Wallet Payment')])
    order_status = models.CharField(max_length=20, 
                                    choices=[('Pending','Pending'),
                                             ('Ordered', 'Ordered'),
                                             ('Shipped', 'Shipped'),
                                             ('Out of delivery','Out of delivery'),
                                             ('Delivered', 'Delivered'),
                                             ('Canceled','Canceled'),
                                             ('Returned','Returned')], 
                                             default='Pending')
    order_date = models.DateTimeField(auto_now_add=True)
    coupon_applied = models.BooleanField(default = False)
    coupon = models.ForeignKey(CouponTable, on_delete=models.SET_NULL, null=True, blank=True)
    coupon_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    offer_applied = models.BooleanField(default = False)
    offer = models.ForeignKey(OfferTable, on_delete=models.SET_NULL, null=True, blank=True)
    is_canceled = models.BooleanField(default=False)
    cancel_description = models.TextField(blank=True, null=True)
    cancel_date = models.DateTimeField(blank=True, null=True)
    is_returned = models.BooleanField(default=False)
    is_refund = models.BooleanField(default=False)
    refund_date = models.DateTimeField(blank=True, null=True)
    razorpay_order_id = models.CharField(max_length=100, null=True, blank=True)
    razorpay_payment_id = models.CharField(max_length=100, null=True, blank=True)
    
    def __str__(self):
        return f"Order {self.order_id} by {self.user.username}"

class OrderAddress(models.Model):
    address_name = models.CharField(max_length=255)  
    street_name = models.CharField(max_length=255)   
    building_no = models.CharField(max_length=100)   
    landmark = models.CharField(max_length=255)      
    city = models.CharField(max_length=100)
    pincode = models.CharField(max_length=20)        
    address_phone = models.CharField(max_length=20)  
    state = models.CharField(max_length=100)
    address_type = models.CharField(                 
        max_length=10,
        choices=[('home', 'Home'), ('office', 'Office')],
        default='home'
    )
    
    def __str__(self):
        return f"{self.address_name}'s {self.address_type} - {self.city}"    

class OrderItem(models.Model):
    order = models.ForeignKey(OrderDetails, on_delete=models.CASCADE, to_field='order_id',db_column='order_id', null=True)
    book = models.ForeignKey(BookTable,on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    price_per_item = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_returned = models.BooleanField(default=False)
    is_canceled = models.BooleanField(default=False)  
    order_status = models.CharField(max_length=20, 
                                    choices=[('Pending','Pending'),
                                             ('Ordered', 'Ordered'),
                                             ('Shipped', 'Shipped'),
                                             ('Delivered', 'Delivered'),
                                             ('Out of delivery','Out of delivery'),
                                             ('Canceled','Canceled'),
                                             ('Returned','Returned')], 
                                             default='Pending')
    
    def has_user_review(self,user,order):
        return ReviewTable.objects.filter(
            user = user,
            book = self.book if hasattr(self,'book') else self,
            order = order
        ).exists
    def __str__(self):
        return f"{self.quantity} x {self.product.name} in Order {self.order.order_id}"
    

class ReturnRequest(models.Model):
    order = models.ForeignKey(OrderDetails, on_delete=models.CASCADE,null=True,blank=True)
    user = models.ForeignKey(UserTable, on_delete=models.CASCADE,null=True,blank=True)
    reason = models.TextField(blank=False, null=False)  # Reason for return
    status = models.CharField(
        max_length=20,
        choices=[
            ('Pending', 'Pending'),
            ('Approved', 'Approved'),
            ('Rejected', 'Rejected'),
            ('Processed', 'Processed')
        ],
        default='Pending'
    )
    return_entire_order = models.BooleanField(default=False)  # Return the entire order
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    admin_note = models.TextField(blank=True, null=True)  # Notes from the admin

    def __str__(self):
        if self.return_entire_order:
            return f"Return Request for Order {self.order.order_id} - {self.status}"
        else:
            # Get related items for this ReturnRequest
            items = self.items.all()  # Access related ReturnItems via related_name='items'
            item_names = ', '.join(item.order_item.book.book_name for item in items)
            return f"Return Request for Items: {item_names} - {self.status}"


class ReturnItem(models.Model):
    return_request = models.ForeignKey(ReturnRequest, on_delete=models.CASCADE, related_name='items')
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE)
    reason = models.TextField(blank=False, null=False)  # Reason for returning this item
    status = models.CharField(
        max_length=20,
        choices=[('Pending', 'Pending'), ('Approved', 'Approved'), ('Rejected', 'Rejected'), ('Processed', 'Processed')],
        default='Pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Return Item for {self.order_item.book.title} - {self.status}"
    
    
class ReviewTable(models.Model):
    order = models.ForeignKey(OrderDetails, on_delete=models.CASCADE, null=True,blank=True)
    user = models.ForeignKey(UserTable,on_delete=models.CASCADE)
    book = models.ForeignKey(BookTable, on_delete=models.CASCADE,null=True,blank=True)
    rating = models.PositiveBigIntegerField(choices=[(i,i) for i in  range(1,6)])
    review = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review for {self.book.book_name} by {self.user.username}"