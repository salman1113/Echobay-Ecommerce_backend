from django.shortcuts import render
from rest_framework import generics, permissions, status, viewsets, filters
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from django.db.models import Q
from .models import Product, CartItem, Wishlist, Order, OrderItem
from .serializers import ( UserSerializer, ProductSerializer, CartItemSerializer, WishlistSerializer, OrderSerializer, CustomUserSerializer)


from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView

# Create your views here.

# --- Authentication ---
class RegisterView(generics.CreateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]


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
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny] # Allow viewing without login
    
    # 2. Add Pagination
    pagination_class = ProductPagination
    
    # 3. Add Search and Ordering Filters
    # SearchFilter handles ?search=...
    # OrderingFilter handles ?ordering=price or ?ordering=-price
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    
    # 4. Define which fields can be searched
    search_fields = ['name', 'description', 'category'] 
    
    # 5. Define which fields can be sorted
    ordering_fields = ['price', 'created_at']

    # 6. Custom Logic for Category Filter
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Get 'category' from URL parameters
        category = self.request.query_params.get('category')
        
        # Filter if category exists and is not "All"
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
        # Add to cart
        product_id = request.data.get('product_id')
        quantity = request.data.get('quantity', 1)
        
        product = Product.objects.get(id=product_id)
        cart_item, created = CartItem.objects.get_or_create(
            user=request.user, product=product
        )
        
        if not created:
            cart_item.quantity += int(quantity)
            cart_item.save()
        
        return Response({'message': 'Added to cart'}, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        # Remove from cart
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
        product = Product.objects.get(id=product_id)
        Wishlist.objects.get_or_create(user=request.user, product=product)
        return Response({'message': 'Added to wishlist'})

    def delete(self, request, pk):
        Wishlist.objects.filter(user=request.user, id=pk).delete()
        return Response({'message': 'Removed'})

# --- Orders & Checkout ---
class OrderView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # 1. Get User Orders
        orders = Order.objects.filter(user=request.user).order_by('-created_at')
        
        # 2. Manual Pagination Logic
        paginator = ProductPagination() # Using the same pagination class we created earlier
        result_page = paginator.paginate_queryset(orders, request)
        
        # 3. Serialize only the current page data
        serializer = OrderSerializer(result_page, many=True)
        
        # 4. Return paginated response (includes count, next, previous links)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        # Checkout logic
        shipping = request.data.get('shipping')
        total = request.data.get('total')
        payment_method = request.data.get('payment_method')
        
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
            
            # Decrease Stock
            item.product.count -= item.quantity
            item.product.save()

        # Clear Cart
        cart_items.delete()

        return Response({'message': 'Order placed successfully', 'order_id': order.id}, status=status.HTTP_201_CREATED)