from django.contrib.auth.models import AbstractUser
from django.db import models

# Create your models here.
class UserTable(AbstractUser):
    phone_number = models.CharField(max_length= 15, null= False, blank= False)
    gender = models.CharField(max_length= 15)
    is_blocked = models.BooleanField(default = False)
    is_deleted = models.BooleanField(default = False)

    groups = models.ManyToManyField('auth.Group', related_name='custom_user_groups', blank=True)
    user_permissions = models.ManyToManyField('auth.Permission', related_name='custom_user_permissions', blank=True)
    def __str__(self):
        return f"{self.username}({self.email})"
    
    class Meta:
        db_table = 'user_detail'