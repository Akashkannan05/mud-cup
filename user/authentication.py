from rest_framework_simplejwt.authentication import JWTAuthentication

class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        header = self.get_header(request)
        raw_token = None

        if header is not None:
            raw_token = self.get_raw_token(header)
            # Support tokens passed without 'Bearer ' prefix in Authorization header
            if raw_token is None:
                try:
                    parts = header.split()
                    if len(parts) == 1:
                        raw_token = parts[0]
                    elif len(parts) == 2:
                        raw_token = parts[1]
                except Exception:
                    pass
        else:
            raw_token = request.COOKIES.get('access_token') or None
            
        if raw_token is None:
            return None
            
        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token
