from rest_framework.permissions import BasePermission
from user.models import UserDetails


class IsAdminOrStaff(BasePermission):
    """
    Custom permission to only allow users with role 'admin' or 'staff' (or is_staff/is_superuser).
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False):
            return True

        # Check role field on UserDetails
        role = getattr(user, 'role', None)
        if not role:
            try:
                userdetails = UserDetails.objects.get(pk=user.pk)
                role = userdetails.role
            except UserDetails.DoesNotExist:
                role = None

        return role in ['admin', 'staff']
