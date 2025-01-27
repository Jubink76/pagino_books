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


class BookTable(models.Model):
    book_name = models.CharField(max_length=100)
    description = models.TextField()
    stock_quantity = models.PositiveIntegerField(default=0)
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    offer_price = models.DecimalField(max_digits=10, decimal_places=2, editable=False, default=0)
    previous_offer_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    publication_date = models.DateField(auto_now_add=True)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, null=True, blank=True)
    language = models.ForeignKey(Language, on_delete=models.CASCADE, null=True, blank=True)
    category = models.ForeignKey(CategoryTable, on_delete=models.CASCADE, null=True, blank=True)
    is_available = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    applied_offer = models.ForeignKey('order_detail_app.OfferTable', null=True, blank=True, 
                                    on_delete=models.SET_NULL, related_name='applied_books')
    additional_offer_applied = models.BooleanField(default=False)

    def calculate_regular_price(self):
        """Calculate the regular discounted price without any offers"""
        regular_discount = (self.base_price * self.discount_percentage) / Decimal('100')
        return self.base_price - regular_discount

    def calculate_offer_price(self, offer):
        """Calculate price with a specific offer based on base price"""
        if not offer:
            return self.calculate_regular_price()
            
        if offer.discount_type == 'percentage':
            # Calculate discount amount from base price
            discount_amount = (self.base_price * Decimal(str(offer.discount_value))) / Decimal('100')
            # Also apply regular discount percentage if any
            regular_discount = (self.base_price * self.discount_percentage) / Decimal('100')
            # Take the larger discount
            final_discount = max(discount_amount, regular_discount)
            return self.base_price - final_discount
        elif offer.discount_type == 'fixed':
            # For fixed discount, first apply the fixed amount to base price
            price_after_fixed = max(self.base_price - Decimal(str(offer.discount_value)), Decimal('0'))
            # Calculate regular discount
            regular_price = self.calculate_regular_price()
            # Return the lower of the two prices
            return min(price_after_fixed, regular_price)
        return self.calculate_regular_price()

    def update_price_with_offer(self, offer=None, skip_save=False):
        """
        Update the book's price with a specific offer or remove offer if None
        Returns True if price was updated, False otherwise
        """
        regular_price = self.calculate_regular_price()
        
        if offer:
            new_price = self.calculate_offer_price(offer)
            # Compare with regular price to determine if offer is better
            if new_price < regular_price:
                self.previous_offer_price = self.offer_price
                self.offer_price = new_price
                self.additional_offer_applied = True
                self.applied_offer = offer
                if not skip_save:
                    self.save(update_fields=[
                        'previous_offer_price',
                        'offer_price',
                        'additional_offer_applied',
                        'applied_offer'
                    ])
                return True
        else:
            # Removing offer
            self.offer_price = regular_price
            self.previous_offer_price = None
            self.additional_offer_applied = False
            self.applied_offer = None
            if not skip_save:
                self.save(update_fields=[
                    'offer_price',
                    'previous_offer_price',
                    'additional_offer_applied',
                    'applied_offer'
                ])
            return True
        return False

    def save(self, *args, **kwargs):
        # Handle basic fields
        self.base_price = Decimal(str(self.base_price))
        self.discount_percentage = Decimal(str(self.discount_percentage or 0))
        self.is_available = self.stock_quantity > 0

        # Only recalculate prices if no offer is applied or if this is a new instance
        if not self.pk or (not self.additional_offer_applied and not self.applied_offer):
            self.offer_price = self.calculate_regular_price()
        elif self.applied_offer and self.applied_offer.is_active:
            self.update_price_with_offer(self.applied_offer, skip_save=True)

        super().save(*args, **kwargs)

    def __str__(self):
        return self.book_name
    

class BookImage(models.Model):
    book = models.ForeignKey(BookTable, on_delete=models.CASCADE,related_name="images")
    image = models.ImageField(upload_to='book_images/')  # Ensure MEDIA_URL and MEDIA_ROOT are configured

    def __str__(self):
        return f"Image for {self.book.book_name}"