from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework import status
from .serializers import LoginSerializer
from .models import UserDetails


class LoginAPIView(APIView):
    """
    API endpoint for User Login returning JWT access and refresh tokens.
    POST /api/user/login/
    Payload: {"username": "<username>", "password": "<password>"}
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)

        role = 'customer'
        if isinstance(user, UserDetails):
            role = user.role
        elif hasattr(user, 'userdetails'):
            role = user.userdetails.role
        elif user.is_superuser:
            role = 'admin'
        elif user.is_staff:
            role = 'staff'

        response = Response({
            'message': 'Login successful',
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh),
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': role,
            }
        }, status=status.HTTP_200_OK)

        response.set_cookie(
            key='access_token',
            value=str(refresh.access_token),
            httponly=True,
            samesite='Lax'
        )
        response.set_cookie(
            key='refresh_token',
            value=str(refresh),
            httponly=True,
            samesite='Lax'
        )

        return response

class CookieTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get('refresh_token')
        if not refresh_token:
            return Response({"detail": "Refresh token not found."}, status=status.HTTP_401_UNAUTHORIZED)
        
        request.data['refresh'] = refresh_token
        
        try:
            response = super().post(request, *args, **kwargs)
            if response.status_code == 200:
                access_token = response.data.get('access')
                if access_token:
                    response.set_cookie(
                        key='access_token',
                        value=access_token,
                        httponly=True,
                        samesite='Lax'
                    )
            return response
        except TokenError as e:
            raise InvalidToken(e.args[0])

class UserMeAPIView(APIView):
    """
    API endpoint to return the currently authenticated user's details.
    GET /api/user/me/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        role = 'customer'
        if isinstance(user, UserDetails):
            role = user.role
        elif hasattr(user, 'userdetails'):
            role = user.userdetails.role
        elif user.is_superuser:
            role = 'admin'
        elif user.is_staff:
            role = 'staff'
            
        return Response({
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': role,
            }
        }, status=status.HTTP_200_OK)
