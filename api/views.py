from django.shortcuts import render
from rest_framework import generics, permissions, status, viewsets, filters
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from django.db.models import Q
from django.contrib.auth import authenticate, login
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Product, CartItem, Wishlist, Order, OrderItem
from .serializers import ( 
    UserSerializer, 
    ProductSerializer, 
    CartItemSerializer, 
    WishlistSerializer, 
    OrderSerializer, 
    CustomUserSerializer
)

from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView
from rest_framework.permissions import AllowAny
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode
from django.core.mail import send_mail
from django.conf import settings



@api_view(['POST'])
@permission_classes([AllowAny])
def custom_password_reset_confirm(request):
    # ഫ്രണ്ടെൻഡിൽ നിന്ന് വരുന്ന ഡാറ്റ
    uidb64 = request.data.get('uid')
    token = request.data.get('token')
    password = request.data.get('new_password1')

    # ഡാറ്റ ഉണ്ടോ എന്ന് നോക്കുന്നു
    if not (uidb64 and token and password):
        return Response({'detail': 'Missing data'}, status=status.HTTP_400_BAD_REQUEST)

    User = get_user_model()
    try:
        # UID ഡീകോഡ് ചെയ്ത് യൂസറെ കണ്ടുപിടിക്കുന്നു
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return Response({'detail': 'Invalid User ID'}, status=status.HTTP_400_BAD_REQUEST)

    # ടോക്കൺ ശരിയാണോ എന്ന് നോക്കുന്നു
    if not default_token_generator.check_token(user, token):
        return Response({'detail': 'Invalid or expired token'}, status=status.HTTP_400_BAD_REQUEST)

    # എല്ലാം ശരിയാണെങ്കിൽ പാസ്‌വേഡ് മാറ്റുന്നു
    user.set_password(password)
    user.save()

    try:
        send_mail(
            subject='Password Reset Successful | EchoBay',
            message=f'Hello {user.username},\n\nYour password has been successfully reset. You can now login with your new password.\n\nIf this was not you, please contact support immediately.\n\nThanks,\nEchoBay Team',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True, # മെയിൽ അയക്കാൻ പറ്റിയില്ലെങ്കിലും എറർ കാണിക്കരുത്
        )
    except Exception as e:
        print(f"Failed to send success email: {e}")

    return Response({'detail': 'Password reset successful'}, status=status.HTTP_200_OK)

# --- Authentication ---

class RegisterView(generics.CreateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]


# 👇 NEW: Custom Login View (For Email Signal & User Data)
class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        
        # 1. Authenticate User
        user = authenticate(username=username, password=password)
        
        if user is not None:
            # 2. 🔥 Trigger Django Login Signal (Sends Email)
            login(request, user)
            
            # 3. Generate Tokens
            refresh = RefreshToken.for_user(user)
            
            # 4. Get User Data
            serializer = CustomUserSerializer(user)

            # 5. Send Response
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': serializer.data
            }, status=status.HTTP_200_OK)
        else:
            return Response({'detail': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)


class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    callback_url = "postmessage"
    client_class = OAuth2Client

    def get_response(self):
        original_response = super().get_response()
        my_user_serializer = CustomUserSerializer(self.user)
        original_response.data['user'] = my_user_serializer.data
        return original_response


# --- Products ---
class ProductPagination(PageNumberPagination):
    page_size = 8
    page_size_query_param = 'page_size'
    max_page_size = 100

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().order_by('-id') 
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny] 
    
    pagination_class = ProductPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description', 'category'] 
    ordering_fields = ['price', 'created_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        category = self.request.query_params.get('category')
        if category and category.lower() != 'all':
            queryset = queryset.filter(category__iexact=category)
        return queryset


# --- Cart ---
class CartView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        cart_items = CartItem.objects.filter(user=request.user)
        serializer = CartItemSerializer(cart_items, many=True)
        return Response(serializer.data)

    def post(self, request):
        product_id = request.data.get('product_id')
        quantity = request.data.get('quantity', 1)
        
        try:
            product = Product.objects.get(id=product_id)
            cart_item, created = CartItem.objects.get_or_create(
                user=request.user, product=product
            )
            
            if not created:
                cart_item.quantity += int(quantity)
                cart_item.save()
            
            return Response({'message': 'Added to cart'}, status=status.HTTP_200_OK)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk):
        CartItem.objects.filter(user=request.user, id=pk).delete()
        return Response({'message': 'Removed'}, status=status.HTTP_200_OK)


# --- Wishlist ---
class WishlistView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        items = Wishlist.objects.filter(user=request.user)
        serializer = WishlistSerializer(items, many=True)
        return Response(serializer.data)

    def post(self, request):
        product_id = request.data.get('product_id')
        try:
            product = Product.objects.get(id=product_id)
            Wishlist.objects.get_or_create(user=request.user, product=product)
            return Response({'message': 'Added to wishlist'})
        except Product.DoesNotExist:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk):
        Wishlist.objects.filter(user=request.user, id=pk).delete()
        return Response({'message': 'Removed'})


# --- Orders & Checkout ---
class OrderView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        orders = Order.objects.filter(user=request.user).order_by('-created_at')
        paginator = ProductPagination()
        result_page = paginator.paginate_queryset(orders, request)
        serializer = OrderSerializer(result_page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        # Checkout logic
        # 👇 Updated to match Frontend variable names (shipping_details, total_amount)
        shipping = request.data.get('shipping_details') 
        total = request.data.get('total_amount')
        payment_method = request.data.get('payment_method', 'cod') # Default to COD if missing
        
        # Check if cart is empty
        cart_items = CartItem.objects.filter(user=request.user)
        if not cart_items.exists():
             return Response({'error': 'Cart is empty'}, status=status.HTTP_400_BAD_REQUEST)

        # Create Order
        order = Order.objects.create(
            user=request.user,
            total_amount=total,
            shipping_details=shipping,
            payment_method=payment_method,
            status='processing'
        )

        # Move Cart items to Order Items
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price
            )
            
            # Decrease Stock (Check if count > quantity to avoid negative stock)
            if item.product.count >= item.quantity:
                item.product.count -= item.quantity
                item.product.save()

        # Clear Cart
        cart_items.delete()

        return Response({'message': 'Order placed successfully', 'order_id': order.id}, status=status.HTTP_201_CREATED)