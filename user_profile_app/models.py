from django.db import models
from log_reg_app.models import UserTable
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver


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