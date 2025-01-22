from django.utils.deprecation import MiddlewareMixin
from django.db import transaction
from decimal import Decimal
from .models import WalletTable

class WalletMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.user.is_authenticated:           
            with transaction.atomic():
                WalletTable.objects.get_or_create(
                    user=request.user,
                    defaults={'available_balance': Decimal('0.00')}
                )
            