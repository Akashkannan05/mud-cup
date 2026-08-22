from django.db import models
from django.contrib.auth.models import User


class UserDetails(User):
    ROLE_CHOICES = (
        ('staff', 'Staff'),
        ('admin', 'Admin'),
        ('customer', 'Customer'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')

    class Meta:
        verbose_name = 'User Detail'
        verbose_name_plural = 'User Details'

    def __str__(self):
        return f"{self.username} ({self.role})"
