from django.urls import path
from .views import LoginAPIView, CookieTokenRefreshView, UserMeAPIView

urlpatterns = [
    path('login/', LoginAPIView.as_view(), name='user-login'),
    path('token/refresh/', CookieTokenRefreshView.as_view(), name='token-refresh'),
    path('me/', UserMeAPIView.as_view(), name='user-me'),
]
