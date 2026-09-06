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
        self.assertIn('access_token', data)
        self.assertIn('refresh_token', data)
        self.assertEqual(data['user']['username'], 'testuser')
        self.assertEqual(data['user']['role'], 'customer')

    def test_token_refresh(self):
        # Obtain tokens first
        login_response = self.client.post(self.url, {
            'username': 'testuser',
            'password': 'securepassword123'
        })
        refresh_token = login_response.json()['refresh_token']

        refresh_url = reverse('token-refresh')
        self.client.cookies['refresh_token'] = refresh_token
        refresh_response = self.client.post(refresh_url)
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


from unittest.mock import patch

class GoogleLoginAPIViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('google-auth-callback')

    @patch('google.oauth2.id_token.verify_oauth2_token')
    def test_google_login_new_user_success(self, mock_verify):
        mock_verify.return_value = {
            'email': 'newgoogleuser@example.com',
            'email_verified': True,
            'given_name': 'New',
            'family_name': 'User',
            'sub': '1234567890'
        }
        payload = {'id_token': 'fake-valid-google-id-token'}
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['message'], 'Google authentication successful')
        self.assertIn('access_token', data)
        self.assertIn('refresh_token', data)
        self.assertEqual(data['user']['email'], 'newgoogleuser@example.com')
        self.assertEqual(data['user']['first_name'], 'New')
        self.assertEqual(data['user']['last_name'], 'User')
        self.assertEqual(data['user']['role'], 'customer')

        # Verify cookies issued
        self.assertIn('access_token', response.cookies)
        self.assertIn('refresh_token', response.cookies)
        self.assertIn('sessionid', response.cookies)

        # Verify DB entry creation
        user = UserDetails.objects.filter(email='newgoogleuser@example.com').first()
        self.assertIsNotNone(user)
        self.assertEqual(user.username, 'newgoogleuser')

    @patch('google.oauth2.id_token.verify_oauth2_token')
    def test_google_login_existing_user_success(self, mock_verify):
        existing_user = UserDetails.objects.create_user(
            username='existinguser',
            email='existing@example.com',
            first_name='Existing',
            last_name='User',
            role='customer'
        )
        mock_verify.return_value = {
            'email': 'existing@example.com',
            'email_verified': True,
            'given_name': 'Existing',
            'family_name': 'User',
            'sub': '0987654321'
        }
        payload = {'id_token': 'fake-valid-google-id-token'}
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['user']['id'], existing_user.id)
        self.assertIn('sessionid', response.cookies)

    def test_google_login_missing_token(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.json())

    @patch('google.oauth2.id_token.verify_oauth2_token')
    def test_google_login_unverified_email(self, mock_verify):
        mock_verify.return_value = {
            'email': 'unverified@example.com',
            'email_verified': False
        }
        payload = {'id_token': 'fake-unverified-token'}
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

