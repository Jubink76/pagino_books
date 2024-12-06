from django.db import models
from adminside_app.models import BookTable
from log_reg_app.models import UserTable
from decimal import Decimal
# Create your models here.

class CartTable(models.Model):
    user = models.ForeignKey(UserTable,on_delete=models.CASCADE,null=True,blank=True)
    book = models.ForeignKey(BookTable,on_delete=models.CASCADE, null=True, blank=True)
    session_id = models.CharField(max_length=255, null=True, blank=True)
    quantity = models.PositiveIntegerField(null=True, blank=True)
    item_price = models.DecimalField(max_digits=10,decimal_places=2,editable=False)
    total_price = models.DecimalField(max_digits=10,decimal_places=2,editable=False)
    grand_total = models.DecimalField(max_digits=10, decimal_places=2, default=0,editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    session_is_available = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        # Calculate item_price if not set
        if not self.item_price and self.book:
            self.item_price = self.book.offer_price if self.book.offer_price else self.book.base_price
        
        # Calculate total_price
        self.total_price = self.item_price * Decimal(str(self.quantity))
        
        # Save the instance
        super().save(*args, **kwargs)
        
        # Update grand_total only if not skipping
        skip_update = kwargs.pop('skip_update', False)
        if not skip_update:
            self.update_grand_total()
    
    def update_grand_total(self):
        # Get related cart items
        if self.user:
            cart_items = CartTable.objects.filter(user=self.user)
        else:
            cart_items = CartTable.objects.filter(session_id=self.session_id)
        
        # Calculate new grand_total
        grand_total = cart_items.aggregate(total=models.Sum('total_price'))['total'] or Decimal('0.00')
        
        # Update all related cart items with skip_update=True to prevent recursion
        cart_items.update(grand_total=grand_total)

    def __str__(self):
        return f"Cart item for {self.book.book_name} (Quantity: {self.quantity})"
    

class WhishlistTable(models.Model):
    user = models.ForeignKey(UserTable,on_delete=models.CASCADE,null=True,blank=True)
    book = models.ForeignKey(BookTable,on_delete=models.CASCADE, null=True, blank=True)
    session_id = models.CharField(max_length=255, null=True, blank=True)
    session_is_available = models.BooleanField(default=True)