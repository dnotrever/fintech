from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from authentication.views import ConfirmEmailView, LogoutView, ResendConfirmationView

urlpatterns = [
    path('login/', TokenObtainPairView.as_view(), name='login'),
    path('refresh/', TokenRefreshView.as_view(), name='refresh'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('confirm/resend/', ResendConfirmationView.as_view(), name='confirm-resend'),
    path('confirm/<str:token>/', ConfirmEmailView.as_view(), name='confirm-email'),
]
