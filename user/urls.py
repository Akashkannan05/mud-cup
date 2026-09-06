from django.urls import path
from .views import LoginAPIView, GoogleLoginAPIView, CookieTokenRefreshView, UserMeAPIView

urlpatterns = [
    path('login/', LoginAPIView.as_view(), name='user-login'),
    path('google/', GoogleLoginAPIView.as_view(), name='google-login'),
    path('token/refresh/', CookieTokenRefreshView.as_view(), name='token-refresh'),
    path('me/', UserMeAPIView.as_view(), name='user-me'),
]

