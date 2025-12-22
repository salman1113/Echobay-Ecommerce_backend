import razorpay
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, permissions, status, filters, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from django.db.models import Sum, Count
from django.contrib.auth import authenticate, login, get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAuthenticatedOrReadOnly

# Email & Tokens
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode
from django.core.mail import send_mail

# Social Auth
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView

# Permissions
from .permissions import IsAdminUser

# Models & Serializers
from .models import Product, ProductImage, CartItem, Wishlist, Order, OrderItem, Address, CancelledOrder 
from .serializers import ( 
    UserSerializer, ProductSerializer, CartItemSerializer, 
    WishlistSerializer, OrderSerializer, CustomUserSerializer, AddressSerializer,
    AdminUserSerializer, AdminOrderSerializer
)

User = get_user_model()
client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

#  AUTHENTICATION
@api_view(['POST'])
@permission_classes([AllowAny])
def custom_password_reset_confirm(request):
    uidb64 = request.data.get('uid')
    token = request.data.get('token')
    password = request.data.get('new_password1')

    if not (uidb64 and token and password):
        return Response({'detail': 'Missing data'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return Response({'detail': 'Invalid User ID'}, status=status.HTTP_400_BAD_REQUEST)

    if not default_token_generator.check_token(user, token):
        return Response({'detail': 'Invalid or expired token'}, status=status.HTTP_400_BAD_REQUEST)

    user.set_password(password)
    user.save()
    return Response({'detail': 'Password reset successful'}, status=status.HTTP_200_OK)

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]

class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)
        if user:
            login(request, user)
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': CustomUserSerializer(user).data
            }, status=status.HTTP_200_OK)
        return Response({'detail': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    callback_url = "postmessage" 
    client_class = OAuth2Client

    def get_response(self):
        response = super().get_response()
        user = self.user
        refresh = RefreshToken.for_user(user)
        response.data['access'] = str(refresh.access_token)
        response.data['refresh'] = str(refresh)
        response.data['user'] = CustomUserSerializer(user).data
        
        return response
    
class ProductPagination(PageNumberPagination):
    page_size = 8
    page_size_query_param = 'page_size'
    max_page_size = 100

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().order_by('-id') 
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticatedOrReadOnly] 
    pagination_class = ProductPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description', 'category'] 
    ordering_fields = ['price', 'created_at']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [AllowAny()]

    def get_queryset(self):
        qs = super().get_queryset()
        category = self.request.query_params.get('category')
        if category and category.lower() != 'all':
            qs = qs.filter(category__iexact=category)
        return qs

#  CART & WISHLIST & ADDRESS
class AddressViewSet(viewsets.ModelViewSet):
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

#  CART & WISHLIST & ADDRESS
class CartView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        serializer = CartItemSerializer(CartItem.objects.filter(user=request.user), many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request):
        pid = request.data.get('product_id')
        qty = int(request.data.get('quantity', 1))
        try:
            prod = Product.objects.get(id=pid)
            if prod.count < qty: return Response({'error': 'Out of stock'}, 400)
            
            item, created = CartItem.objects.get_or_create(user=request.user, product=prod)
            item.quantity = qty if created else item.quantity + qty
            if item.quantity > 5: return Response({'error': 'Limit exceeded'}, 400)
            item.save()
            return Response({'message': 'Added to cart'})
        except Product.DoesNotExist:
            return Response({'error': 'Product not found'}, 404)
    def delete(self, request, pk):
        CartItem.objects.filter(user=request.user, id=pk).delete()
        return Response({'message': 'Removed'})

class WishlistView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        serializer = WishlistSerializer(Wishlist.objects.filter(user=request.user), many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request):
        try:
            prod = Product.objects.get(id=request.data.get('product_id'))
            Wishlist.objects.get_or_create(user=request.user, product=prod)
            return Response({'message': 'Added'})
        except Product.DoesNotExist: return Response({'error': 'Product not found'}, 404)
    def delete(self, request, pk):
        Wishlist.objects.filter(user=request.user, id=pk).delete()
        return Response({'message': 'Removed'})

#  USER ORDER MANAGEMENT
class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = ProductPagination 

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Order.objects.all().order_by('-created_at')
        return Order.objects.filter(user=self.request.user).order_by('-created_at')

class OrderCheckoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        shipping = request.data.get('shipping_details') 
        total = request.data.get('total_amount')
        method = request.data.get('payment_method', 'cod')
        
        if not shipping or not total: return Response({'error': 'Missing details'}, 400)
        
        cart = CartItem.objects.filter(user=request.user)
        if not cart.exists(): return Response({'error': 'Cart empty'}, 400)

        try:
            status_val = 'processing' if method == 'cod' else 'pending_payment'
            order = Order.objects.create(
                user=request.user, total_amount=total, 
                shipping_details=shipping, payment_method=method, status=status_val
            )
            for item in cart:
                OrderItem.objects.create(order=order, product=item.product, quantity=item.quantity, price=item.product.price)
                if item.product.count >= item.quantity:
                    item.product.count -= item.quantity
                    item.product.save()
            cart.delete()
            return Response({'message': 'Success', 'order_id': order.id, 'status': status_val}, 201)
        except Exception as e: return Response({'error': str(e)}, 500)

class CancelOrderView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, pk):
        try:
            order = Order.objects.get(id=pk) if request.user.is_superuser else Order.objects.get(id=pk, user=request.user)
            if order.status in ['delivered', 'cancelled']: return Response({'error': 'Cannot cancel'}, 400)
            order.status = 'cancelled'
            order.save()
            
            CancelledOrder.objects.create(order=order, cancelled_by=request.user, reason=request.data.get('reason', 'User request'))
            for item in order.items.all():
                item.product.count += item.quantity
                item.product.save()
            return Response({'message': 'Cancelled'}, 200)
        except Order.DoesNotExist: return Response({'error': 'Not found'}, 404)

class RetryPaymentView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, pk):
        try:
            order = Order.objects.get(id=pk, user=request.user)
            if order.status != 'pending_payment': return Response({'error': 'Not pending'}, 400)
            
            amt = int(float(order.total_amount) * 100)
            rzp_order = client.order.create({"amount": amt, "currency": "INR", "payment_capture": "1"})
            
            return Response({
                'razorpay_order_id': rzp_order['id'], 'amount': amt, 
                'currency': 'INR', 'key_id': settings.RAZORPAY_KEY_ID, 'order_id': order.id
            }, 200)
        except Exception as e: return Response({'error': str(e)}, 500)

class CreatePaymentView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        try:
            amt = int(float(request.data.get('total_amount')) * 100)
            order = client.order.create({"amount": amt, "currency": "INR", "payment_capture": "1"})
            return Response({'razorpay_order_id': order['id'], 'amount': amt, 'currency': 'INR', 'key_id': settings.RAZORPAY_KEY_ID}, 200)
        except Exception as e: return Response({'error': str(e)}, 500)

class VerifyPaymentView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        try:
            data = request.data
            client.utility.verify_payment_signature({
                'razorpay_order_id': data['razorpay_order_id'],
                'razorpay_payment_id': data['razorpay_payment_id'],
                'razorpay_signature': data['razorpay_signature']
            })
            if data.get('order_id'):
                Order.objects.filter(id=data['order_id']).update(status='processing', razorpay_payment_id=data['razorpay_payment_id'])
            return Response({'message': 'Verified'}, 200)
        except Exception as e: return Response({'error': str(e)}, 400)

#  ADMIN PANEL
class AdminProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().order_by('-id')
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'category']

    def get_queryset(self):
        qs = super().get_queryset()
        category = self.request.query_params.get('category')
        if category and category != 'All':
            qs = qs.filter(category__iexact=category)
        return qs

    # CREATE: Handles Files AND Links
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.save()

        # 1. Handle File Uploads
        images = request.FILES.getlist('uploaded_images')
        for img in images:
            ProductImage.objects.create(product=product, image=img)
        
        # 2. Handle External URLs (Paste Link)
        image_urls = request.POST.getlist('image_urls')
        for url in image_urls:
            if url.strip(): 
                ProductImage.objects.create(product=product, external_url=url)
        
        # 3. Handle Main Image (Legacy)
        if 'image' in request.FILES:
            product.image = request.FILES['image']
            product.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    # UPDATE: Handles Files AND Links
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        # 1. Delete Removed Images (Pazhaya images kalayan)
        deleted_ids = request.POST.getlist('deleted_image_ids')
        for img_id in deleted_ids:
            if img_id == "main":
                instance.image = None
                instance.save()
            elif img_id.isdigit():
                ProductImage.objects.filter(id=img_id, product=instance).delete()

        # 2. Add New Uploads
        images = request.FILES.getlist('uploaded_images')
        for img in images:
            ProductImage.objects.create(product=instance, image=img)

        # 3. Add New Links
        image_urls = request.POST.getlist('image_urls')
        for url in image_urls:
            if url.strip():
                ProductImage.objects.create(product=instance, external_url=url)

        # 4. Main Image Update (Optional)
        if 'image' in request.FILES:
            instance.image = request.FILES['image']
            instance.save()

        return Response(serializer.data)

class AdminUserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = AdminUserSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    filter_backends = [filters.SearchFilter]
    search_fields = ['username', 'email']

class AdminOrderViewSet(viewsets.ModelViewSet):
    serializer_class = AdminOrderSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def get_queryset(self):
        queryset = Order.objects.all().order_by('-created_at')
        user_id = self.request.query_params.get('user') 
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        return queryset
    
# 4. Admin Dashboard Analytics
class AdminDashboardStatsView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def get(self, request):
        total_products_sold = OrderItem.objects.filter(
            order__status__in=['processing', 'shipped', 'delivered']
        ).aggregate(total=Sum('quantity'))['total'] or 0

        total_revenue = Order.objects.exclude(
            status='cancelled'
        ).aggregate(total=Sum('total_amount'))['total'] or 0

        total_customers = User.objects.filter(is_superuser=False).count()

        data = {
            "total_users": total_customers, 
            "total_products": Product.objects.count(),
            "total_orders": Order.objects.count(),
            "products_sold": total_products_sold,
            "total_revenue": total_revenue,
        }
        return Response(data)