from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
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

        return Response({
            'message': 'Login successful',
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': role,
            }
        }, status=status.HTTP_200_OK)
