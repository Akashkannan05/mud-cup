from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from .models import UserDetails


class UserDetailsModelTests(TestCase):
    def test_create_user_details(self):
        user_detail = UserDetails.objects.create_user(
            username='johndoe',
            email='john@example.com',
            password='password123',
            role='customer'
        )
        self.assertEqual(user_detail.username, 'johndoe')
        self.assertEqual(user_detail.role, 'customer')
        self.assertEqual(str(user_detail), 'johndoe (customer)')

    def test_user_details_role_choices(self):
        staff_user = UserDetails.objects.create_user(
            username='staffuser',
            password='password123',
            role='staff'
        )
        admin_user = UserDetails.objects.create_user(
            username='adminuser',
            password='password123',
            role='admin'
        )
        self.assertEqual(staff_user.role, 'staff')
        self.assertEqual(admin_user.role, 'admin')


class LoginAPIViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = UserDetails.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='securepassword123',
            role='customer'
        )
        self.url = reverse('user-login')

    def test_login_success_returns_access_and_refresh_tokens(self):
        payload = {
            'username': 'testuser',
            'password': 'securepassword123'
        }
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['message'], 'Login successful')
        self.assertIn('access', data)
        self.assertIn('refresh', data)
        self.assertEqual(data['user']['username'], 'testuser')
        self.assertEqual(data['user']['role'], 'customer')

    def test_token_refresh(self):
        # Obtain tokens first
        login_response = self.client.post(self.url, {
            'username': 'testuser',
            'password': 'securepassword123'
        })
        refresh_token = login_response.json()['refresh']

        refresh_url = reverse('token-refresh')
        refresh_response = self.client.post(refresh_url, {'refresh': refresh_token})
        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        self.assertIn('access', refresh_response.json())

    def test_login_wrong_password(self):
        payload = {
            'username': 'testuser',
            'password': 'wrongpassword'
        }
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.json())

    def test_login_non_existent_user(self):
        payload = {
            'username': 'nonexistent',
            'password': 'password123'
        }
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_inactive_user(self):
        self.user.is_active = False
        self.user.save()
        payload = {
            'username': 'testuser',
            'password': 'securepassword123'
        }
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
