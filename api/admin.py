from django.contrib import admin

# Register your models here.

from django.contrib import admin
from .models import User, Product, Order, OrderItem, CartItem, Wishlist, CancelledOrder, Address

# Register the Custom User Model
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'role', 'is_blocked', 'is_active')
    list_filter = ('role', 'is_blocked')
    search_fields = ('username', 'email')

# Register the Product Model
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'count', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('name', 'description')

# Register the Order Model
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'total_amount', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'id')

# Register other models simply
admin.site.register(CartItem)
admin.site.register(Wishlist)
admin.site.register(Address)


@admin.register(CancelledOrder)
class CancelledOrderAdmin(admin.ModelAdmin):
    list_display = ('order', 'cancelled_by', 'refund_status', 'cancelled_at')
    list_filter = ('refund_status', 'cancelled_at')

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'product', 'quantity', 'price') # ടേബിളിൽ കാണിക്കേണ്ടവ
    list_filter = ('order',) # ഫിൽറ്റർ ചെയ്യാൻ
    search_fields = ('product__name', 'order__id') # സെർച്ച് ചെയ്യാൻ