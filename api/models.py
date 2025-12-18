from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator # 👈 Validation Tool

# 1. Custom User Model
class User(AbstractUser):
    ROLE_CHOICES = (('admin', 'Admin'), ('user', 'User'))
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    is_blocked = models.BooleanField(default=False)

# 2. 🆕 Address Model (For User Profile - Multiple Addresses)
class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    street = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=10)
    is_default = models.BooleanField(default=False) # Default address for checkout

    def __str__(self):
        return f"{self.name}, {self.city}"

# 3. Product Model
class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    # 👇 വില 0-ൽ കുറയാൻ പാടില്ല (Validation)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    # 👇 സ്റ്റോക്ക് മൈനസ് ആകില്ല (Positive Integer)
    count = models.PositiveIntegerField(default=0) 
    category = models.CharField(max_length=100)
    images = models.JSONField(default=list) 
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

# 4. Cart Model
class CartItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cart_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    # 👇 കുറഞ്ഞത് 1 എണ്ണമെങ്കിലും വേണം
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])

# 5. Wishlist Model
class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

# 6. Order Model
class Order(models.Model):
    STATUS_CHOICES = (
        ('pending_payment', 'Pending Payment'), # 👈 പേയ്മെന്റ് പരാജയപ്പെട്ടാൽ ഈ സ്റ്റാറ്റസ് വരും
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled')
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    
    # 👇 ടോട്ടൽ എമൗണ്ട് നെഗറ്റീവ് ആകരുത്
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending_payment')
    created_at = models.DateTimeField(auto_now_add=True)
    
    # 👇 അഡ്രസ്സ് JSON ആയി സൂക്ഷിക്കുന്നു (യൂസർ പ്രൊഫൈലിൽ അഡ്രസ്സ് മാറ്റിയാലും ഓർഡർ ഹിസ്റ്ററി മാറില്ല)
    shipping_details = models.JSONField(default=dict) 
    payment_method = models.CharField(max_length=50, default='cod')

    # 👇 Razorpay Payment Integration Fields (NEW)
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.product.name} (Order #{self.order.id})"


# 👇 NEW: Cancelled Order Table (ട്രാക്കിംഗിന് വേണ്ടി)
class CancelledOrder(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='cancellation_details')
    reason = models.TextField(default="Changed mind") # കാരണം
    cancelled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True) # ആര് ക്യാൻസൽ ചെയ്തു
    refund_status = models.CharField(max_length=20, default='pending') # പണം തിരിച്ചുകൊടുത്തോ?
    cancelled_at = models.DateTimeField(auto_now_add=True) # എപ്പോൾ

    def __str__(self):
        return f"Cancelled Order #{self.order.id}"