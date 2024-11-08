from django.db import models

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
    book_name = models.CharField(max_length = 100)
    description = models.TextField()
    stock_quantity = models.PositiveIntegerField(default=0)
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    offer_price = models.DecimalField(max_digits=10, decimal_places=2, editable=False, default=0)
    publication_date = models.DateField(auto_now_add=True)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, null=True, blank=True)
    language = models.ForeignKey(Language, on_delete=models.CASCADE, null=True, blank=True)
    category = models.ForeignKey(CategoryTable, on_delete=models.CASCADE, null=True, blank=True)
    is_available = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        # Convert to float if they're not already in numeric format
        if isinstance(self.base_price, str):
            self.base_price = float(self.base_price)
        if isinstance(self.discount_percentage, str):
            self.discount_percentage = float(self.discount_percentage)

        # Calculate the discount amount and offer price
        discount_amount = (self.base_price * self.discount_percentage) / 100
        self.offer_price = self.base_price - discount_amount

        super().save(*args, **kwargs)


    def __str__(self):
        return self.title
    

class BookImage(models.Model):
    book = models.ForeignKey(BookTable, on_delete=models.CASCADE,related_name="images")
    image = models.ImageField(upload_to='book_images/')  # Ensure MEDIA_URL and MEDIA_ROOT are configured

    def __str__(self):
        return f"Image for {self.book.title}"