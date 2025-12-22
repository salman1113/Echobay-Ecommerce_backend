from rest_framework import serializers
from django.contrib.auth import get_user_model
# 👇 Change 1: ProductImage ഇംപോർട്ട് ചെയ്തു
from .models import Product, ProductImage, CartItem, Wishlist, Order, OrderItem, Address, CancelledOrder 

from dj_rest_auth.serializers import UserDetailsSerializer
from allauth.socialaccount.models import SocialAccount
from dj_rest_auth.serializers import PasswordResetSerializer
from django.conf import settings
from django.contrib.auth.forms import PasswordResetForm

User = get_user_model()

# ==========================================
#  1. USER SERIALIZERS
# ==========================================
class CustomUserSerializer(UserDetailsSerializer):
    image = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()

    class Meta(UserDetailsSerializer.Meta):
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'name', 'image', 'role', 'is_superuser', 'is_active', 'date_joined')
        read_only_fields = ('email', 'role', 'is_superuser', 'date_joined')

    def get_image(self, user):
        try:
            google_account = SocialAccount.objects.get(user=user, provider='google')
            url = google_account.extra_data.get('picture')
            
            # Google Loop fix
            if url and ('googleusercontent.com/profile/picture' in url or '/0' in url):
                return None 

            if url and url.startswith('http://'):
                url = url.replace('http://', 'https://')
            return url
        except SocialAccount.DoesNotExist:
            return None

    def get_name(self, user):
        full_name = f"{user.first_name} {user.last_name}".strip()
        return full_name if full_name else user.username

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'role']

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            role='user'
        )
        return user

class AdminUserSerializer(serializers.ModelSerializer):
    order_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'date_joined', 'is_active', 'order_count', 'is_superuser']

    def get_order_count(self, user):
        return Order.objects.filter(user=user).count()


# ==========================================
#  2. PRODUCT SERIALIZER (✅ FIXED)
# ==========================================
class ProductSerializer(serializers.ModelSerializer):
    images = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = '__all__'

    def get_images(self, obj):
        request = self.context.get('request') 
        image_list = []
        
        # 1. Main Image
        if obj.image:
            try:
                url = request.build_absolute_uri(obj.image.url) if request else obj.image.url
                image_list.append({"id": "main", "url": url})
            except: pass

        # 2. Gallery Images (Safe Fetching Added Here too)
        # 👇 Change: Product Page Crash ആകാതിരിക്കാൻ ഇവിടെയും Safe check ഇട്ടു
        images = getattr(obj, 'images', None) or getattr(obj, 'productimage_set', None)
        
        if images:
            for img in images.all():
                if img.image:
                    try:
                        url = request.build_absolute_uri(img.image.url) if request else img.image.url
                        image_list.append({"id": img.id, "url": url})
                    except: pass
                else:
                    image_list.append({"id": img.id, "url": img.external_url})
                
        return image_list

    def validate_price(self, value):
        if value <= 0: raise serializers.ValidationError("Price must be greater than 0.")
        return value

    def validate_count(self, value):
        if value < 0: raise serializers.ValidationError("Stock count cannot be negative.")
        return value


# ==========================================
#  3. CART & WISHLIST SERIALIZERS
# ==========================================
class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), source='product', write_only=True
    )

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_id', 'quantity']

class WishlistSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), source='product', write_only=True
    )

    class Meta:
        model = Wishlist
        fields = ['id', 'product', 'product_id']


# ==========================================
#  4. ORDER SERIALIZERS (✅ FIXED)
# ==========================================
class CancelledOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = CancelledOrder
        fields = ['reason', 'cancelled_at', 'refund_status']

class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_name = serializers.ReadOnlyField(source='product.name')
    product_image = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderItem
        fields = ['product', 'product_name', 'product_image', 'quantity', 'price']

    def get_product_image(self, obj):
        if not obj.product: return None
        
        image_url = None
        request = self.context.get('request')

        # 1. Main Image ഉണ്ടോ എന്ന് നോക്കുന്നു
        if obj.product.image:
            try:
                image_url = obj.product.image.url
            except: pass
        
        # 2. Main Image ഇല്ലെങ്കിൽ Gallery-യിൽ നോക്കുന്നു
        if not image_url:
            images = getattr(obj.product, 'images', None) or getattr(obj.product, 'productimage_set', None)
            if images and images.exists():
                first_img = images.first()
                if first_img.image:
                    try:
                        image_url = first_img.image.url
                    except: pass
                elif first_img.external_url:
                    return first_img.external_url # External URL ആണെങ്കിൽ നേരിട്ട് കൊടുക്കാം

        # 3. URL കിട്ടിയെങ്കിൽ അത് Full URL ആക്കി മാറ്റുന്നു
        if image_url:
            if request:
                return request.build_absolute_uri(image_url)
            # Request ഇല്ലെങ്കിൽ നമ്മൾ മാനുവലായി ലോക്കൽഹോസ്റ്റ് ചേർക്കുന്നു (Fallback)
            return f"http://127.0.0.1:8000{image_url}"

        return None
        
class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    cancellation_details = CancelledOrderSerializer(read_only=True)
    user = CustomUserSerializer(read_only=True) 
    
    class Meta:
        model = Order
        fields = [
            'id', 'user', 'total_amount', 'status', 'created_at', 
            'shipping_details', 'items', 'payment_method', 'cancellation_details'
        ]

class AdminOrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    user_email = serializers.ReadOnlyField(source='user.email')
    username = serializers.ReadOnlyField(source='user.username')

    class Meta:
        model = Order
        fields = ['id', 'user_email', 'username', 'total_amount', 'status', 'created_at', 'shipping_details', 'items']


# ==========================================
#  5. ADDRESS & PASSWORD RESET
# ==========================================
class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ['id', 'name', 'phone', 'street', 'city', 'state', 'zip_code', 'is_default']
        read_only_fields = ['user']

class CustomPasswordResetSerializer(PasswordResetSerializer):
    def get_email_options(self):
        return {
            'domain_override': 'localhost:5173',
            'email_template_name': 'registration/password_reset_email.html',
            'extra_email_context': {
                'site_name': 'EchoBay'
            }
        }
    
    def save(self):
        request = self.context.get('request')
        opts = {
            'use_https': request.is_secure(),
            'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', None),
            'request': request,
        }
        opts.update(self.get_email_options())

        self.reset_form = PasswordResetForm(data=self.initial_data)
        if self.reset_form.is_valid():
            self.reset_form.save(**opts)