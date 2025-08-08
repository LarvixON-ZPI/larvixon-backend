from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from .models import UserProfile, User
from analysis.models import VideoAnalysis
from typing import Type


class UserModelTest(TestCase):
    """
    Test cases for User model.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )

    def test_user_creation(self):
        """Test user creation with email as username field."""
        self.assertEqual(self.user.email, 'test@example.com')
        self.assertEqual(self.user.username, 'testuser')
        self.assertTrue(self.user.check_password('testpass123'))
        self.assertEqual(str(self.user), 'test@example.com')

    def test_user_profile_creation(self):
        """Test that user profile is created automatically."""
        # Profile should be created via signal or in views
        profile = UserProfile.objects.create(user=self.user)
        self.assertEqual(profile.user, self.user)
        self.assertEqual(str(profile), 'test@example.com - Profile')


class UserRegistrationTest(APITestCase):
    """
    Test cases for user registration.
    """

    def setUp(self):
        self.registration_url = reverse('accounts:register')
        self.valid_payload = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'newpass123',
            'password_confirm': 'newpass123',
            'first_name': 'New',
            'last_name': 'User'
        }

    def test_user_registration_success(self):
        """Test successful user registration."""
        response = self.client.post(self.registration_url, self.valid_payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('user', response.data)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['message'],
                         'User registered successfully')

        # Check user was created
        user = User.objects.get(email='newuser@example.com')
        self.assertEqual(user.username, 'newuser')

    def test_user_registration_password_mismatch(self):
        """Test registration with password mismatch."""
        payload = self.valid_payload.copy()
        payload['password_confirm'] = 'differentpass'
        response = self.client.post(self.registration_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_registration_duplicate_email(self):
        """Test registration with duplicate email."""
        User.objects.create_user(
            username='existing',
            email='newuser@example.com',
            password='pass123'
        )
        response = self.client.post(self.registration_url, self.valid_payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_registration_weak_password(self):
        """Test registration with weak password."""
        payload = self.valid_payload.copy()
        payload['password'] = '123'
        payload['password_confirm'] = '123'
        response = self.client.post(self.registration_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class UserLoginTest(APITestCase):
    """
    Test cases for user login.
    """

    def setUp(self):
        self.login_url = reverse('accounts:login')
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_user_login_success(self):
        """Test successful user login."""
        payload = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        response = self.client.post(self.login_url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('user', response.data)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['message'], 'Login successful')

    def test_user_login_invalid_credentials(self):
        """Test login with invalid credentials."""
        payload = {
            'email': 'test@example.com',
            'password': 'wrongpass'
        }
        response = self.client.post(self.login_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_login_inactive_user(self):
        """Test login with inactive user."""
        self.user.is_active = False
        self.user.save()
        payload = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        response = self.client.post(self.login_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class UserProfileTest(APITestCase):
    """
    Test cases for user profile management.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile = UserProfile.objects.create(user=self.user)
        self.client.force_authenticate(user=self.user)
        self.profile_url = reverse('accounts:profile')
        self.profile_details_url = reverse('accounts:profile-details')

    def test_get_user_profile(self):
        """Test retrieving user profile."""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'test@example.com')

    def test_update_user_profile(self):
        """Test updating user profile."""
        payload = {
            'first_name': 'Updated',
            'last_name': 'Name'
        }
        response = self.client.patch(self.profile_url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Updated')
        self.assertEqual(self.user.last_name, 'Name')

    def test_get_profile_details(self):
        """Test retrieving profile details."""
        response = self.client.get(self.profile_details_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_profile_details(self):
        """Test updating profile details."""
        payload = {
            'bio': 'Updated bio',
            'organization': 'Test Org',
            'phone_number': '+1234567890'
        }
        response = self.client.patch(self.profile_details_url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.bio, 'Updated bio')
        self.assertEqual(self.profile.organization, 'Test Org')


class PasswordChangeTest(APITestCase):
    """
    Test cases for password change.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='oldpass123'
        )
        self.client.force_authenticate(user=self.user)
        self.password_change_url = reverse('accounts:password-change')

    def test_password_change_success(self):
        """Test successful password change."""
        payload = {
            'old_password': 'oldpass123',
            'new_password': 'newpass123',
            'confirm_password': 'newpass123'
        }
        response = self.client.post(self.password_change_url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newpass123'))

    def test_password_change_wrong_old_password(self):
        """Test password change with wrong old password."""
        payload = {
            'old_password': 'wrongpass',
            'new_password': 'newpass123',
            'confirm_password': 'newpass123'
        }
        response = self.client.post(self.password_change_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_change_mismatch(self):
        """Test password change with password mismatch."""
        payload = {
            'old_password': 'oldpass123',
            'new_password': 'newpass123',
            'confirm_password': 'differentpass'
        }
        response = self.client.post(self.password_change_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class VideoAnalysisTest(APITestCase):
    """
    Test cases for video analysis management.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        self.analysis_list_url = reverse('accounts:analysis-list')

        # Create some test analyses
        self.analysis1 = VideoAnalysis.objects.create(
            user=self.user,
            video_name='test_video1.mp4',
            video_file_path='/path/to/video1.mp4',
            status='completed'
        )
        self.analysis2 = VideoAnalysis.objects.create(
            user=self.user,
            video_name='test_video2.mp4',
            video_file_path='/path/to/video2.mp4',
            status='pending'
        )

    def test_get_analysis_list(self):
        """Test retrieving analysis list."""
        response = self.client.get(self.analysis_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_create_analysis(self):
        """Test creating new analysis."""
        payload = {
            'video_name': 'new_video.mp4',
            'video_file_path': '/path/to/new_video.mp4'
        }
        response = self.client.post(self.analysis_list_url, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(VideoAnalysis.objects.count(), 3)

    def test_get_analysis_detail(self):
        """Test retrieving specific analysis."""
        detail_url = reverse('accounts:analysis-detail',
                             args=[self.analysis1.id])
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['video_name'], 'test_video1.mp4')

    def test_update_analysis(self):
        """Test updating analysis with user feedback."""
        detail_url = reverse('accounts:analysis-detail',
                             args=[self.analysis1.id])
        payload = {
            'actual_substance': 'cocaine',
            'user_feedback': 'The analysis was accurate'
        }
        response = self.client.patch(detail_url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.analysis1.refresh_from_db()
        self.assertEqual(self.analysis1.actual_substance, 'cocaine')

    def test_user_stats(self):
        """Test getting user statistics."""
        stats_url = reverse('accounts:user-stats')
        response = self.client.get(stats_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_analyses'], 2)
        self.assertEqual(response.data['completed_analyses'], 1)
        self.assertEqual(response.data['pending_analyses'], 1)


class AuthenticationTest(APITestCase):
    """
    Test cases for authentication and authorization.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile_url = reverse('accounts:profile')

    def test_unauthenticated_access(self):
        """Test that unauthenticated users cannot access protected endpoints."""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_access(self):
        """Test that authenticated users can access protected endpoints."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_jwt_token_authentication(self):
        """Test JWT token authentication."""
        # Get tokens
        login_url = reverse('accounts:login')
        payload = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        response = self.client.post(login_url, payload)
        access_token = response.data['access']

        # Use token to access protected endpoint
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
