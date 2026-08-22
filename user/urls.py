from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import LoginAPIView

urlpatterns = [
    path('login/', LoginAPIView.as_view(), name='user-login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
]
