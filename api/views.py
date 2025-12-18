import razorpay
from django.conf import settings
from django.shortcuts import render, get_object_or_404
from rest_framework import generics, permissions, status, viewsets, filters
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from django.db.models import Q
from django.contrib.auth import authenticate, login
from rest_framework_simplejwt.tokens import RefreshToken

# Models & Serializers
from .models import Product, CartItem, Wishlist, Order, OrderItem, Address, CancelledOrder 
from .serializers import ( 
    UserSerializer, 
    ProductSerializer, 
    CartItemSerializer, 
    WishlistSerializer, 
    OrderSerializer, 
    CustomUserSerializer,
    AddressSerializer
)

# Auth & Social Imports
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView
from rest_framework.permissions import AllowAny
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode
from django.core.mail import send_mail

# 👇 RAZORPAY SETUP
client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

# --- Password Reset ---
@api_view(['POST'])
@permission_classes([AllowAny])
def custom_password_reset_confirm(request):
    uidb64 = request.data.get('uid')
    token = request.data.get('token')
    password = request.data.get('new_password1')

    if not (uidb64 and token and password):
        return Response({'detail': 'Missing data'}, status=status.HTTP_400_BAD_REQUEST)

    User = get_user_model()
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return Response({'detail': 'Invalid User ID'}, status=status.HTTP_400_BAD_REQUEST)

    if not default_token_generator.check_token(user, token):
        return Response({'detail': 'Invalid or expired token'}, status=status.HTTP_400_BAD_REQUEST)

    user.set_password(password)
    user.save()

    try:
        send_mail(
            subject='Password Reset Successful | EchoBay',
            message=f'Hello {user.username},\n\nYour password has been successfully reset.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )
    except Exception as e:
        print(f"Failed to send success email: {e}")

    return Response({'detail': 'Password reset successful'}, status=status.HTTP_200_OK)


# --- Authentication ---
class RegisterView(generics.CreateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]

class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)
        
        if user is not None:
            login(request, user)
            refresh = RefreshToken.for_user(user)
            serializer = CustomUserSerializer(user)

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


# --- Address Management ---
class AddressViewSet(viewsets.ModelViewSet):
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# --- Cart ---
class CartView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        cart_items = CartItem.objects.filter(user=request.user)
        serializer = CartItemSerializer(cart_items, many=True)
        return Response(serializer.data)

    def post(self, request):
        product_id = request.data.get('product_id')
        qty_to_add = int(request.data.get('quantity', 1))
        MAX_QTY_PER_USER = 5  # ✅ Max Limit Logic

        try:
            product = Product.objects.get(id=product_id)

            # 🛑 Stock & Limit Checks
            if product.count <= 0:
                return Response({'error': 'Out of stock'}, status=status.HTTP_400_BAD_REQUEST)
            if product.count < qty_to_add:
                return Response({'error': f'Only {product.count} items left!'}, status=status.HTTP_400_BAD_REQUEST)

            cart_item, created = CartItem.objects.get_or_create(user=request.user, product=product)

            current_qty = cart_item.quantity if not created else 0
            new_total_qty = current_qty + qty_to_add
            
            if new_total_qty > MAX_QTY_PER_USER:
                return Response({'error': f'Limit exceeded! Max {MAX_QTY_PER_USER} units allowed per person.'}, status=status.HTTP_400_BAD_REQUEST)
            
            if new_total_qty > product.count:
                 return Response({'error': f'Not enough stock available.'}, status=status.HTTP_400_BAD_REQUEST)

            if not created:
                cart_item.quantity = new_total_qty
            else:
                cart_item.quantity = qty_to_add
            
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


# --- 💰 PAYMENT VIEWS (Razorpay) ---

# 1. Create Order in Razorpay
class CreatePaymentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        total_amount = request.data.get('total_amount')
        try:
            # Convert to paise
            amount_in_paise = int(float(total_amount) * 100)
            
            razorpay_order = client.order.create({
                "amount": amount_in_paise,
                "currency": "INR",
                "payment_capture": "1"
            })
            
            return Response({
                'razorpay_order_id': razorpay_order['id'],
                'amount': amount_in_paise,
                'currency': 'INR',
                'key_id': settings.RAZORPAY_KEY_ID
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# 2. Verify Payment & Update Order
class VerifyPaymentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            data = request.data
            
            # Verify Signature
            client.utility.verify_payment_signature({
                'razorpay_order_id': data['razorpay_order_id'],
                'razorpay_payment_id': data['razorpay_payment_id'],
                'razorpay_signature': data['razorpay_signature']
            })

            # Update Order Status
            order_id = data.get('order_id')
            if order_id:
                order = Order.objects.get(id=order_id)
                order.status = 'processing' # ✅ Payment Success
                order.razorpay_payment_id = data['razorpay_payment_id']
                order.save()

            return Response({'message': 'Payment Successful'}, status=status.HTTP_200_OK)

        except razorpay.errors.SignatureVerificationError:
            return Response({'error': 'Payment Verification Failed'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# 3. 👇 NEW: Retry Payment View (For Pending Orders)
class RetryPaymentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            # ഓർഡർ കണ്ടുപിടിക്കുന്നു
            order = Order.objects.get(id=pk, user=request.user)

            # സ്റ്റാറ്റസ് Pending Payment അല്ലെങ്കിൽ റിജക്ട് ചെയ്യുക
            if order.status != 'pending_payment':
                return Response({'error': 'This order is not pending payment'}, status=status.HTTP_400_BAD_REQUEST)

            # Razorpay-യിൽ പുതിയ ഓർഡർ ഐഡി ഉണ്ടാക്കുന്നു
            amount_in_paise = int(float(order.total_amount) * 100)
            
            razorpay_order = client.order.create({
                "amount": amount_in_paise,
                "currency": "INR",
                "payment_capture": "1"
            })

            return Response({
                'razorpay_order_id': razorpay_order['id'],
                'amount': amount_in_paise,
                'currency': 'INR',
                'key_id': settings.RAZORPAY_KEY_ID,
                'order_id': order.id
            }, status=status.HTTP_200_OK)

        except Order.DoesNotExist:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
        shipping = request.data.get('shipping_details') 
        total = request.data.get('total_amount')
        payment_method = request.data.get('payment_method', 'cod')
        
        if not shipping or not total:
             return Response({'error': 'Missing shipping details or total amount'}, status=status.HTTP_400_BAD_REQUEST)

        cart_items = CartItem.objects.filter(user=request.user)
        if not cart_items.exists():
             return Response({'error': 'Cart is empty'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # ✅ Determine Status based on Payment Method
            initial_status = 'processing' if payment_method == 'cod' else 'pending_payment'

            # Create Order
            order = Order.objects.create(
                user=request.user,
                total_amount=total,
                shipping_details=shipping,
                payment_method=payment_method,
                status=initial_status
            )

            # Move Items
            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    price=item.product.price
                )
                
                # Decrease Stock
                if item.product.count >= item.quantity:
                    item.product.count -= item.quantity
                    item.product.save()

            # Clear Cart
            cart_items.delete()

            return Response({
                'message': 'Order placed successfully', 
                'order_id': order.id,
                'status': initial_status
            }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# 👇 UPDATED: Cancel Order View (With Database Tracking)
class CancelOrderView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            # ലോഗിൻ ചെയ്ത യൂസറുടെ ഓർഡർ ആണോ എന്ന് ഉറപ്പുവരുത്തുന്നു
            order = Order.objects.get(id=pk, user=request.user)
            
            # ഡെലിവറി കഴിഞ്ഞാൽ ക്യാൻസൽ ചെയ്യാൻ പാടില്ല
            if order.status == 'delivered':
                return Response({'error': 'Cannot cancel delivered order'}, status=status.HTTP_400_BAD_REQUEST)
            
            if order.status == 'cancelled':
                return Response({'error': 'Order is already cancelled'}, status=status.HTTP_400_BAD_REQUEST)

            # 1. സ്റ്റാറ്റസ് മാറ്റുന്നു
            order.status = 'cancelled'
            order.save()
            
            # 2. 👇 പുതിയ ടേബിളിൽ റെക്കോർഡ് ഇടുന്നു
            CancelledOrder.objects.create(
                order=order,
                cancelled_by=request.user,
                reason=request.data.get('reason', 'User cancelled from dashboard') 
            )

            # 3. സ്റ്റോക്ക് തിരിച്ചിടുന്നു (Restock)
            # ഓർഡർ ക്യാൻസൽ ചെയ്താൽ ആ സാധനങ്ങൾ തിരിച്ച് സ്റ്റോക്കിൽ കയറണം.
            for item in order.items.all():
                item.product.count += item.quantity
                item.product.save()

            return Response({'message': 'Order cancelled successfully and restocked'}, status=status.HTTP_200_OK)
        
        except Order.DoesNotExist:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)