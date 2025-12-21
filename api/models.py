from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from decimal import Decimal

# 1. Custom User Model
class User(AbstractUser):
    ROLE_CHOICES = (('admin', 'Admin'), ('user', 'User'))
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    is_blocked = models.BooleanField(default=False)

# 2. Address Model
class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    street = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=10)
    is_default = models.BooleanField(default=False) 

    def __str__(self):
        return f"{self.name}, {self.city}"

# 3. Product Model
class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    count = models.PositiveIntegerField(default=0) 
    category = models.CharField(max_length=100)
    
    # ✅ FIX: Main Image (Thumbnail) - കാർഡുകളിൽ കാണിക്കാൻ
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

# ✅ NEW: Product Gallery (For Multiple Images)
# backend/api/models.py

class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='products/gallery/', null=True, blank=True) # 👈 അപ്‌ലോഡ് ചെയ്യാൻ
    external_url = models.URLField(max_length=500, null=True, blank=True) # 👈 ലിങ്ക് കൊടുക്കാൻ (പുതിയത്)
    
    def __str__(self):
        return f"{self.product.name} Image"

# 4. Cart Model
class CartItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cart_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])

# 5. Wishlist Model
class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

# 6. Order Model
class Order(models.Model):
    STATUS_CHOICES = (
        ('pending_payment', 'Pending Payment'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled')
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending_payment')
    created_at = models.DateTimeField(auto_now_add=True)
    shipping_details = models.JSONField(default=dict) 
    payment_method = models.CharField(max_length=50, default='cod')
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.product.name} (Order #{self.order.id})"

# 7. Cancelled Order
class CancelledOrder(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='cancellation_details')
    reason = models.TextField(default="Changed mind") 
    cancelled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True) 
    refund_status = models.CharField(max_length=20, default='pending') 
    cancelled_at = models.DateTimeField(auto_now_add=True) 

    def __str__(self):
        return f"Cancelled Order #{self.order.id}"