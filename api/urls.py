from django.urls import path, include
from rest_framework.routers import DefaultRouter
from dj_rest_auth.views import (
    UserDetailsView, 
    PasswordChangeView, 
    PasswordResetView, 
    PasswordResetConfirmView
)
from .views import (
    RegisterView, 
    LoginView,          
    ProductViewSet, 
    CartView, 
    WishlistView, 
    OrderView, 
    GoogleLogin,
    AddressViewSet,
    custom_password_reset_confirm,
    # 👇 NEW: Payment Views Impoerted
    CreatePaymentView, 
    VerifyPaymentView,
    CancelOrderView,
    RetryPaymentView
)
from rest_framework_simplejwt.views import TokenRefreshView
from .serializers import CustomPasswordResetSerializer

router = DefaultRouter()
router.register(r'products', ProductViewSet)
router.register(r'addresses', AddressViewSet, basename='addresses')

urlpatterns = [
    # --- Authentication ---
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'), 
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/google/', GoogleLogin.as_view(), name='google_login'),

    # --- Profile & Password Management ---
    path('user/', UserDetailsView.as_view(), name='user_details'),
    path('password/change/', PasswordChangeView.as_view(), name='rest_password_change'),

    # Password Reset
    path('password/reset/', PasswordResetView.as_view(serializer_class=CustomPasswordResetSerializer), name='rest_password_reset'),
    path('password/reset/confirm/<uidb64>/<token>/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password/reset/confirm/', custom_password_reset_confirm, name='password_reset_confirm_api'),

    # --- Shop Logic ---
    path('', include(router.urls)), 
    path('cart/', CartView.as_view(), name='cart'),
    path('cart/<int:pk>/', CartView.as_view(), name='cart-delete'),
    path('wishlist/', WishlistView.as_view(), name='wishlist'),
    path('wishlist/<int:pk>/', WishlistView.as_view(), name='wishlist-delete'),
    path('orders/', OrderView.as_view(), name='orders'),

    # 👇 --- Payment URLs (Razorpay) ---
    path('payment/create/', CreatePaymentView.as_view(), name='create-payment'),
    path('payment/verify/', VerifyPaymentView.as_view(), name='verify-payment'),
    path('orders/<int:pk>/cancel/', CancelOrderView.as_view(), name='cancel-order'),
    path('orders/<int:pk>/retry-payment/', RetryPaymentView.as_view(), name='retry-payment'),
]