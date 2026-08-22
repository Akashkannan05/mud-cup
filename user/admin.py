from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import UserDetails


@admin.register(UserDetails)
class UserDetailsAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('Role Details', {'fields': ('role',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Role Details', {'fields': ('role',)}),
    )
