from rest_framework import serializers
from .models import User, Product, CartItem, Wishlist, Order, OrderItem

# --- NEW IMPORTS FOR GOOGLE AUTH ---
from dj_rest_auth.serializers import UserDetailsSerializer
from allauth.socialaccount.models import SocialAccount

from dj_rest_auth.serializers import PasswordResetSerializer
from django.conf import settings
from django.contrib.auth.forms import PasswordResetForm

# 1. Custom User Serializer (For Login Response: Returns Image & Name)
class CustomUserSerializer(UserDetailsSerializer):
    profile_image = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()

    class Meta(UserDetailsSerializer.Meta):
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'name', 'profile_image', 'role')
        read_only_fields = ('email', 'role')

    def get_profile_image(self, user):
        # ഗൂഗിൾ അക്കൗണ്ടിൽ നിന്ന് ഫോട്ടോ എടുക്കുന്നു
        try:
            google_account = SocialAccount.objects.get(user=user, provider='google')
            return google_account.extra_data.get('picture')
        except SocialAccount.DoesNotExist:
            return None

    def get_name(self, user):
        # ഫസ്റ്റ് നെയിമും ലാസ്റ്റ് നെയിമും ചേർത്ത് ഫുൾ നെയിം ആക്കുന്നു
        full_name = f"{user.first_name} {user.last_name}".strip()
        return full_name if full_name else user.username

# 2. User Serializer (For Manual Registration)
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

# 3. Product Serializer
class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'

# 4. Cart Serializer
class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), source='product', write_only=True
    )

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_id', 'quantity']

# 5. Wishlist Serializer
class WishlistSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), source='product', write_only=True
    )

    class Meta:
        model = Wishlist
        fields = ['id', 'product', 'product_id']

# 6. Order Serializers
class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    class Meta:
        model = OrderItem
        fields = ['product', 'quantity', 'price']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = Order
        fields = ['id', 'total_amount', 'status', 'created_at', 'shipping_details', 'items']


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
        # Allauth-നെ ഒഴിവാക്കി, നേരിട്ട് Django Form ഉപയോഗിക്കുന്നു
        opts = {
            'use_https': request.is_secure(),
            'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', None),
            'request': request,
        }
        opts.update(self.get_email_options())

        # Standard Django PasswordResetForm
        self.reset_form = PasswordResetForm(data=self.initial_data)
        
        if self.reset_form.is_valid():
            self.reset_form.save(**opts)