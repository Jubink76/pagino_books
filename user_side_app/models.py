from django.db import models
from adminside_app.models import BookTable
from log_reg_app.models import UserTable
# Create your models here.

class CartTable(models.Model):
    user = models.ForeignKey(UserTable,on_delete=models.CASCADE,null=True,blank=True)
    book = models.ForeignKey(BookTable,on_delete=models.CASCADE, null=True, blank=True)
    session_id = models.CharField(max_length=255, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    item_price = models.DecimalField(max_digits=10,decimal_places=2,editable=False)
    total_price = models.DecimalField(max_digits=10,decimal_places=2,editable=False)
    grand_total = models.DecimalField(max_digits=10,decimal_places=2,editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
