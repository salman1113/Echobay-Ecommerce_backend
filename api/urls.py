from django.urls import path, include
from rest_framework.routers import DefaultRouter
from dj_rest_auth.views import (
    UserDetailsView, PasswordChangeView, PasswordResetView, PasswordResetConfirmView
)
from .views import (
    RegisterView, LoginView, GoogleLogin, custom_password_reset_confirm,
    ProductViewSet, CartView, WishlistView, AddressViewSet,
    OrderViewSet, OrderCheckoutView, CancelOrderView, RetryPaymentView,
    CreatePaymentView, VerifyPaymentView,
    AdminProductViewSet, 
    AdminUserViewSet, 
    AdminOrderViewSet, 
    AdminDashboardStatsView
)
from rest_framework_simplejwt.views import TokenRefreshView
from .serializers import CustomPasswordResetSerializer

#  ROUTER SETUP 
router = DefaultRouter()

# Public & User Routes
router.register(r'products', ProductViewSet, basename='products')
router.register(r'addresses', AddressViewSet, basename='addresses')
router.register(r'orders', OrderViewSet, basename='user-orders')

# Admin Routes
router.register(r'admin/products', AdminProductViewSet, basename='admin-products')
router.register(r'admin/users', AdminUserViewSet, basename='admin-users')
router.register(r'admin/orders', AdminOrderViewSet, basename='admin-orders')

urlpatterns = [
    #  Authentication 
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'), 
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/google/', GoogleLogin.as_view(), name='google_login'),

    #  Profile & Password 
    path('user/', UserDetailsView.as_view(), name='user_details'),
    path('password/change/', PasswordChangeView.as_view(), name='password_change'),
    path('password/reset/', PasswordResetView.as_view(serializer_class=CustomPasswordResetSerializer), name='password_reset'),
    path('password/reset/confirm/<uidb64>/<token>/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password/reset/confirm/', custom_password_reset_confirm, name='password_reset_confirm_api'),

    #  Shopping Logic 
    path('cart/', CartView.as_view(), name='cart'),
    path('cart/<int:pk>/', CartView.as_view(), name='cart-delete'),
    path('wishlist/', WishlistView.as_view(), name='wishlist'),
    path('wishlist/<int:pk>/', WishlistView.as_view(), name='wishlist-delete'),

    # Order Actions 
    path('orders/checkout/', OrderCheckoutView.as_view(), name='order-checkout'), 
    path('orders/<int:pk>/cancel/', CancelOrderView.as_view(), name='cancel-order'),
    path('orders/<int:pk>/retry-payment/', RetryPaymentView.as_view(), name='retry-payment'),

    # Payments
    path('payment/create/', CreatePaymentView.as_view(), name='create-payment'),
    path('payment/verify/', VerifyPaymentView.as_view(), name='verify-payment'),

    # Admin Dashboard Stats 
    path('admin/stats/', AdminDashboardStatsView.as_view(), name='admin-stats'),

    # Router Includes
    path('', include(router.urls)), 
]