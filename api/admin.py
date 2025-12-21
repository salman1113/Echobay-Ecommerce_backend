from django.contrib import admin
from .models import User, Product, ProductImage, Order, OrderItem, CartItem, Wishlist, CancelledOrder, Address

# ✅ 1. Product Image Inline (ഇത് പ്രോഡക്റ്റിന്റെ കൂടെ താഴെ ഇമേജ് ചേർക്കാൻ സഹായിക്കും)
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1  # ഒരു സമയം ഒരു എക്സ്ട്രാ ബോക്സ് കാണിക്കും

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
    
    # 👇 ഈ വരിയാണ് മൾട്ടിപ്പിൾ ഇമേജ് കാണിക്കുന്നത്
    inlines = [ProductImageInline] 

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
# admin.site.register(ProductImage) # Inline കൊടുത്തത് കൊണ്ട് ഇത് വേണമെന്നില്ല

@admin.register(CancelledOrder)
class CancelledOrderAdmin(admin.ModelAdmin):
    list_display = ('order', 'cancelled_by', 'refund_status', 'cancelled_at')
    list_filter = ('refund_status', 'cancelled_at')

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'product', 'quantity', 'price') 
    list_filter = ('order',) 
    search_fields = ('product__name', 'order__id')