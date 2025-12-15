from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.

# 1. Custom User Model
class User(AbstractUser):
    ROLE_CHOICES = (('admin', 'Admin'), ('user', 'User'))
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    is_blocked = models.BooleanField(default=False)
    
    # i use 'username' for login by default in Django

# Product Model
class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    count = models.IntegerField(default=0) # Stock quantity Aaahn ith
    category = models.CharField(max_length=100)
    # Storing images as a list of URLs ["url1", "url2"]
    images = models.JSONField(default=list) 
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

# Cart Model
class CartItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cart_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

# Wishlist Model
class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

# Order Model
class Order(models.Model):
    STATUS_CHOICES = (
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled')
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='processing')
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Store shipping address as JSON to match to the frontend requirement
    shipping_details = models.JSONField(default=dict) 
    payment_method = models.CharField(max_length=50, default='cod')

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2) # Price at the time of purchase