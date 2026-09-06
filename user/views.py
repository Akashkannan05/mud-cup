import uuid
import requests
from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.models import User
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests
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
            samesite='None',
            secure=True
        )
        response.set_cookie(
            key='refresh_token',
            value=str(refresh),
            httponly=True,
            samesite='None',
            secure=True
        )

        return response


class GoogleLoginAPIView(APIView):
    """
    API endpoint for Google OAuth verification.
    POST /api/auth/callback/google or /api/user/google/
    Payload: {"id_token": "<token>"} or {"token": "<token>"} or {"credential": "<token>"} or {"access_token": "<access_token>"}
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        token = request.data.get('id_token') or request.data.get('token') or request.data.get('credential')
        access_token = request.data.get('access_token')

        if not token and not access_token:
            return Response(
                {"detail": "Google authentication token (id_token, credential, or access_token) is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user_info = None

        if token:
            client_id = getattr(settings, 'GOOGLE_CLIENT_ID', '') or None
            try:
                id_info = google_id_token.verify_oauth2_token(
                    token,
                    google_requests.Request(),
                    audience=client_id if client_id else None
                )
                user_info = id_info
            except Exception:
                try:
                    resp = requests.get('https://oauth2.googleapis.com/tokeninfo', params={'id_token': token}, timeout=10)
                    if resp.status_code == 200:
                        data = resp.json()
                        if client_id and data.get('aud') != client_id:
                            return Response({"detail": "Token audience mismatch."}, status=status.HTTP_400_BAD_REQUEST)
                        user_info = data
                except Exception as req_err:
                    return Response({"detail": f"Failed to verify Google token: {str(req_err)}"}, status=status.HTTP_400_BAD_REQUEST)

        elif access_token:
            try:
                resp = requests.get(
                    'https://www.googleapis.com/oauth2/v3/userinfo',
                    headers={'Authorization': f'Bearer {access_token}'},
                    timeout=10
                )
                if resp.status_code == 200:
                    user_info = resp.json()
            except Exception as req_err:
                return Response({"detail": f"Failed to verify Google access token: {str(req_err)}"}, status=status.HTTP_400_BAD_REQUEST)

        if not user_info:
            return Response({"detail": "Invalid or expired Google token."}, status=status.HTTP_400_BAD_REQUEST)

        email = user_info.get('email')
        email_verified = user_info.get('email_verified')
        if isinstance(email_verified, str):
            email_verified = email_verified.lower() == 'true'

        if not email or not email_verified:
            return Response({"detail": "Google account email is not provided or not verified."}, status=status.HTTP_400_BAD_REQUEST)

        name_from_google = user_info.get('name') or ''
        first_name = user_info.get('given_name') or (name_from_google.split(' ')[0] if name_from_google else '')
        last_name = user_info.get('family_name') or (' '.join(name_from_google.split(' ')[1:]) if ' ' in name_from_google else '')

        # Look up existing user
        user = UserDetails.objects.filter(email__iexact=email).first()
        if not user:
            base_user = User.objects.filter(email__iexact=email).first()
            if base_user:
                if hasattr(base_user, 'userdetails'):
                    user = base_user.userdetails
                else:
                    user = UserDetails(user_ptr=base_user, role='customer')
                    user.__dict__.update(base_user.__dict__)
                    user.save()
            else:
                base_username = email.split('@')[0]
                username = base_username
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}_{uuid.uuid4().hex[:6]}"

                user = UserDetails.objects.create_user(
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    role='customer'
                )
                user.set_unusable_password()
                user.save()

        updated = False
        if first_name and user.first_name != first_name:
            user.first_name = first_name
            updated = True
        if last_name and user.last_name != last_name:
            user.last_name = last_name
            updated = True
        if updated:
            user.save()

        # Issue Django session cookie (sessionid)
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')

        # Issue SimpleJWT tokens
        refresh = RefreshToken.for_user(user)

        role = user.role if isinstance(user, UserDetails) else getattr(getattr(user, 'userdetails', None), 'role', 'customer')
        full_name = f"{user.first_name} {user.last_name}".strip() or user.username

        response = Response({
            'message': 'Google authentication successful',
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh),
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'name': full_name,
                'role': role,
            }
        }, status=status.HTTP_200_OK)

        response.set_cookie(
            key='access_token',
            value=str(refresh.access_token),
            httponly=True,
            samesite='None',
            secure=True
        )
        response.set_cookie(
            key='refresh_token',
            value=str(refresh),
            httponly=True,
            samesite='None',
            secure=True
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
                        samesite='None',
                        secure=True
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
            
        full_name = f"{user.first_name} {user.last_name}".strip() or user.username
        return Response({
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'name': full_name,
                'role': role,
            }
        }, status=status.HTTP_200_OK)

