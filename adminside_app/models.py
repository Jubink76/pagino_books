from django.db import models
from decimal import Decimal
from datetime import datetime

# Create your models here.
class CategoryTable(models.Model):
    category_name = models.CharField(max_length=100)
    description = models.TextField()
    is_available = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    def __str__(self):
        return self.category_name
    

class Author(models.Model):
    name = models.CharField(max_length=100)
    bio = models.TextField(blank=True)

    def __str__(self):
        return self.name
    
class Language(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name
    

def calculate_offer_price(base_price, offer_type, discount_type, discount_value):
    """
    Utility function to calculate the price after applying an offer.
    """
    if discount_type == 'percentage':
        discount_amount = (base_price * Decimal(discount_value)) / Decimal(100)
        return base_price - discount_amount
    elif discount_type == 'fixed':
        return max(base_price - Decimal(discount_value), Decimal(0))
    return base_price 


class BookTable(models.Model):
    book_name = models.CharField(max_length = 100)
    description = models.TextField()
    stock_quantity = models.PositiveIntegerField(default=0)
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    offer_price = models.DecimalField(max_digits=10, decimal_places=2, editable=False, default=0)
    previous_offer_price = models.DecimalField(max_digits=10, decimal_places=2,null=True, blank=True)
    publication_date = models.DateField(auto_now_add=True)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, null=True, blank=True)
    language = models.ForeignKey(Language, on_delete=models.CASCADE, null=True, blank=True)
    category = models.ForeignKey(CategoryTable, on_delete=models.CASCADE, null=True, blank=True)
    is_available = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    applied_offer = models.ForeignKey('order_detail_app.OfferTable',null=True,blank=True,on_delete=models.SET_NULL,related_name='applied_books')
    additional_offer_applied = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        from order_detail_app.models import OfferTable  # Import locally to avoid circular imports

        self.base_price = Decimal(self.base_price)
        self.discount_percentage = Decimal(self.discount_percentage or 0)
        self.is_available = self.stock_quantity > 0

        # Calculate regular offer price
        regular_discount = (self.base_price * self.discount_percentage) / Decimal(100)
        regular_offer_price = self.base_price - regular_discount

        # Fetch active offers
        now = datetime.now()
        active_product_offer = OfferTable.objects.filter(
            product=self, offer_type='product', is_active=True,
            valid_from__lte=now, valid_to__gte=now
        ).first()

        active_category_offer = OfferTable.objects.filter(
            category=self.category, offer_type='category', is_active=True,
            valid_from__lte=now, valid_to__gte=now
        ).first()

        # Calculate additional offer prices
        def calculate_offer_price(base_price, discount_type, discount_value):
            if discount_type == 'percentage':
                discount_amount = (base_price * Decimal(discount_value)) / Decimal(100)
                return base_price - discount_amount
            elif discount_type == 'fixed':
                return max(base_price - Decimal(discount_value), Decimal(0))
            return base_price  # Fallback

        product_offer_price = calculate_offer_price(
            self.base_price,
            active_product_offer.discount_type if active_product_offer else None,
            active_product_offer.discount_value if active_product_offer else 0
        )

        category_offer_price = calculate_offer_price(
            self.base_price,
            active_category_offer.discount_type if active_category_offer else None,
            active_category_offer.discount_value if active_category_offer else 0
        )

        # Determine the lowest price among regular, product, and category offers
        self.previous_offer_price = self.offer_price
        self.offer_price = min(regular_offer_price, product_offer_price, category_offer_price)

        # Update flag for additional offers
        self.additional_offer_applied = self.offer_price < regular_offer_price

        super().save(*args, **kwargs)



    def __str__(self):
        return self.title
    

class BookImage(models.Model):
    book = models.ForeignKey(BookTable, on_delete=models.CASCADE,related_name="images")
    image = models.ImageField(upload_to='book_images/')  # Ensure MEDIA_URL and MEDIA_ROOT are configured

    def __str__(self):
        return f"Image for {self.book.book_name}"