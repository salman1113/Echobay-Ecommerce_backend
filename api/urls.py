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
    custom_password_reset_confirm  # ✅ ഇത് ഇംപോർട്ട് ചെയ്തിട്ടുണ്ടെന്ന് ഉറപ്പുവരുത്തുക
)
from rest_framework_simplejwt.views import TokenRefreshView
from .serializers import CustomPasswordResetSerializer

router = DefaultRouter()
router.register(r'products', ProductViewSet)

urlpatterns = [
    # --- Authentication ---
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'), 
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/google/', GoogleLogin.as_view(), name='google_login'),

    # --- Profile & Password Management ---
    path('user/', UserDetailsView.as_view(), name='user_details'),
    path('password/change/', PasswordChangeView.as_view(), name='rest_password_change'),

    # 👇 1. Password Reset Request (Email Sending)
    path('password/reset/', PasswordResetView.as_view(serializer_class=CustomPasswordResetSerializer), name='rest_password_reset'),

    # 👇 2. Link Generation (Django needs this to create the email link)
    # ഇത് മാറ്റരുത്, ഇമെയിൽ ലിങ്ക് ജനറേറ്റ് ചെയ്യാൻ ഇത് ആവശ്യമാണ്.
    path('password/reset/confirm/<uidb64>/<token>/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),

    # 👇 3. API Endpoint (React POSTs data here) - 🔥 UPDATED
    # ഇവിടെയാണ് നമ്മൾ നമ്മുടെ പുതിയ Custom Function കണക്ട് ചെയ്തത്.
    path('password/reset/confirm/', custom_password_reset_confirm, name='password_reset_confirm_api'),

    # --- Shop Logic ---
    path('', include(router.urls)), 
    path('cart/', CartView.as_view(), name='cart'),
    path('cart/<int:pk>/', CartView.as_view(), name='cart-delete'),
    path('wishlist/', WishlistView.as_view(), name='wishlist'),
    path('wishlist/<int:pk>/', WishlistView.as_view(), name='wishlist-delete'),
    path('orders/', OrderView.as_view(), name='orders'),
]