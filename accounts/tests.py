from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import UserProfile, User


class UserModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
        )

    def test_user_creation(self):
        """Test user creation with email as username field."""
        self.assertEqual(self.user.email, "test@example.com")
        self.assertEqual(self.user.username, "testuser")
        self.assertTrue(self.user.check_password("testpass123"))
        self.assertEqual(str(self.user), "test@example.com")

    def test_user_profile_creation(self):
        """Test that user profile is created automatically."""
        # Profile should be created via signal or in views
        profile = UserProfile.objects.create(user=self.user)
        self.assertEqual(profile.user, self.user)
        self.assertEqual(str(profile), "test@example.com - Profile")


class UserRegistrationTest(APITestCase):
    def setUp(self):
        self.registration_url = reverse("accounts:register")
        self.valid_payload = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "newpass123",
            "password_confirm": "newpass123",
            "first_name": "New",
            "last_name": "User",
        }

    def test_user_registration_success(self):
        response = self.client.post(self.registration_url, self.valid_payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("user", response.data)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["message"], "User registered successfully")

        # Check user was created
        user = User.objects.get(email="newuser@example.com")
        self.assertEqual(user.username, "newuser")

    def test_user_registration_password_mismatch(self):
        payload = self.valid_payload.copy()
        payload["password_confirm"] = "differentpass"
        response = self.client.post(self.registration_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_registration_duplicate_email(self):
        User.objects.create_user(
            username="existing", email="newuser@example.com", password="pass123"
        )
        response = self.client.post(self.registration_url, self.valid_payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_registration_weak_password(self):
        payload = self.valid_payload.copy()
        payload["password"] = "123"
        payload["password_confirm"] = "123"
        response = self.client.post(self.registration_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class UserLoginTest(APITestCase):
    def setUp(self):
        self.login_url = reverse("accounts:login")
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    def test_user_login_success(self):
        payload = {"email": "test@example.com", "password": "testpass123"}
        response = self.client.post(self.login_url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("user", response.data)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["message"], "Login successful")

    def test_user_login_invalid_credentials(self):
        payload = {"email": "test@example.com", "password": "wrongpass"}
        response = self.client.post(self.login_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_login_inactive_user(self):
        self.user.is_active = False
        self.user.save()
        payload = {"email": "test@example.com", "password": "testpass123"}
        response = self.client.post(self.login_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class UserProfileTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.profile = UserProfile.objects.create(user=self.user)
        self.client.force_authenticate(user=self.user)
        self.profile_url = reverse("accounts:profile")
        self.profile_details_url = reverse("accounts:profile-details")

    def test_get_user_profile(self):
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "test@example.com")

    def test_update_user_profile(self):
        payload = {"first_name": "Updated", "last_name": "Name"}
        response = self.client.patch(self.profile_url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Updated")
        self.assertEqual(self.user.last_name, "Name")

    def test_get_profile_details(self):
        response = self.client.get(self.profile_details_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_profile_details(self):
        payload = {
            "bio": "Updated bio",
            "organization": "Test Org",
            "phone_number": "+1234567890",
        }
        response = self.client.patch(self.profile_details_url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.bio, "Updated bio")
        self.assertEqual(self.profile.organization, "Test Org")


class PasswordChangeTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="oldpass123"
        )
        self.client.force_authenticate(user=self.user)
        self.password_change_url = reverse("accounts:password-change")

    def test_password_change_success(self):
        payload = {
            "old_password": "oldpass123",
            "new_password": "newpass123",
            "confirm_password": "newpass123",
        }
        response = self.client.post(self.password_change_url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("newpass123"))

    def test_password_change_wrong_old_password(self):
        payload = {
            "old_password": "wrongpass",
            "new_password": "newpass123",
            "confirm_password": "newpass123",
        }
        response = self.client.post(self.password_change_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_change_mismatch(self):
        payload = {
            "old_password": "oldpass123",
            "new_password": "newpass123",
            "confirm_password": "differentpass",
        }
        response = self.client.post(self.password_change_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class AuthenticationTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.profile_url = reverse("accounts:profile")

    def test_unauthenticated_access(self):
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_access(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_jwt_token_authentication(self):
        # Get tokens
        login_url = reverse("accounts:login")
        payload = {"email": "test@example.com", "password": "testpass123"}
        response = self.client.post(login_url, payload)
        access_token = response.data["access"]

        # Use token to access protected endpoint
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
