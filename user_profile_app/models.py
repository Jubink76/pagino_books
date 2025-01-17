from django.db import models
from log_reg_app.models import UserTable
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils.timezone import now
from django.utils import timezone

# Create your models here.
class AddressTable(models.Model):
    address_name=models.CharField(max_length=100)
    street_name=models.CharField(max_length=100)
    building_no = models.CharField(max_length=100)
    landmark = models.CharField(max_length=250)
    city = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    address_phone = models.CharField(max_length=15)
    state = models.CharField(max_length=100)
    user = models.ForeignKey(UserTable, on_delete=models.CASCADE, related_name="addresses", null=True, blank=True)
    is_default = models.BooleanField(default = False)
    address_type = models.CharField(max_length=20,
                                    choices=[('home','home'),
                                             ('office','office')],
                                             default='home')
    class Meta:
        db_table = 'Address Table'
        ordering = ['-is_default', 'id']


@receiver(post_save, sender=AddressTable)
def ensure_default_address(sender, instance, created, **kwargs):
    if created:  # Only run this when a new address is created
        user_addresses = AddressTable.objects.filter(user=instance.user)
        
        # If this is the only address, make it default
        if user_addresses.count() == 1:
            instance.is_default = True
            instance.save()
        # If this is a new address and there are no default addresses, make the first one default
        elif not user_addresses.filter(is_default=True).exists():
            first_address = user_addresses.first()
            if first_address:
                first_address.is_default = True
                first_address.save()

@receiver(post_delete, sender=AddressTable)
def set_new_default_after_delete(sender, instance, **kwargs):
    if instance.is_default:
        # If the deleted address was default, make the first remaining address default
        first_address = AddressTable.objects.filter(user=instance.user).first()
        if first_address:
            first_address.is_default = True
            first_address.save()


class WalletTable(models.Model):
    user = models.OneToOneField('log_reg_app.UserTable', on_delete=models.CASCADE, related_name='wallet')
    available_balance = models.DecimalField(max_digits=10,decimal_places=2,default=0.00)
    def __str__(self):
        return f"Wallet of {self.user.phone_number}"

class WalletTransaction(models.Model):
    TRANSACTION_TYPE_CHOICES = [
        ('add', 'Added to wallet'),
        ('deduct', 'Deducted from wallet'),
        ('refund', 'Refunded'),
    ]

    wallet = models.ForeignKey(WalletTable, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPE_CHOICES)
    transaction_amount = models.DecimalField(max_digits=10, decimal_places=2,default=0.00)
    description = models.TextField(blank=True, null=True)
    transaction_time = models.DateTimeField(default=now)

    def __str__(self):
        return f"Transaction: {self.transaction_type} - {self.transaction_amount} on {self.transaction_time}"