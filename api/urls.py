from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RegisterView, ProductViewSet, CartView, WishlistView, OrderView, GoogleLogin
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

router = DefaultRouter()
router.register(r'products', ProductViewSet)

urlpatterns = [
    # Authentication
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'), # Returns Access + Refresh Token
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Shop Logic
    path('', include(router.urls)), # Handles /products/ and /products/<id>/
    path('cart/', CartView.as_view(), name='cart'),
    path('cart/<int:pk>/', CartView.as_view(), name='cart-delete'),
    path('wishlist/', WishlistView.as_view(), name='wishlist'),
    path('wishlist/<int:pk>/', WishlistView.as_view(), name='wishlist-delete'),
    path('orders/', OrderView.as_view(), name='orders'),

    path('auth/google/', GoogleLogin.as_view(), name='google_login'),
]