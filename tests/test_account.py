import sys
from django.test import TestCase
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate
from accounts.models import User
from accounts.views.authentication import UserRegistrationView, UserLoginView
from accounts.views.profile import (
    UserProfileView,
    UserProfileDetailView,
    UserProfileStats,
)
from tests.common import TestFixtures, run_tests


class TestAuthentication(TestCase):
    def setUp(self) -> None:
        self.factory = APIRequestFactory()
        self.user_data: dict[str, str] = TestFixtures.get_test_user_data()

    def test_user_registration(self) -> None:
        request: Request = self.factory.post(
            "/accounts/register/", self.user_data, format="json"
        )
        response: Response = UserRegistrationView.as_view()(request)

        self.assertEqual(response.status_code, 201)
        self.assertIn("user", response.data)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["message"], "User registered successfully")

    def test_user_login(self) -> None:
        User.objects.create_user(
            username=self.user_data["username"],
            email=self.user_data["email"],
            password=self.user_data["password"],
        )

        login_data: dict[str, str] = {
            "email": self.user_data["email"],
            "password": self.user_data["password"],
        }

        request: Request = self.factory.post(
            "/accounts/login/", login_data, format="json"
        )
        response: Response = UserLoginView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertIn("user", response.data)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["message"], "Login successful")

    def test_invalid_login(self) -> None:
        User.objects.create_user(
            username=self.user_data["username"],
            email=self.user_data["email"],
            password=self.user_data["password"],
        )

        invalid_data: dict[str, str] = {
            "email": self.user_data["email"],
            "password": "wrongpassword",
        }

        request: Request = self.factory.post(
            "/accounts/login/", invalid_data, format="json"
        )
        response: Response = UserLoginView.as_view()(request)

        self.assertEqual(response.status_code, 400)

    def test_duplicate_registration(self) -> None:
        User.objects.create_user(
            username=self.user_data["username"],
            email=self.user_data["email"],
            password=self.user_data["password"],
        )

        request: Request = self.factory.post(
            "/accounts/register/", self.user_data, format="json"
        )
        response: Response = UserRegistrationView.as_view()(request)

        self.assertEqual(response.status_code, 400)


class TestUserProfile(TestCase):
    def setUp(self) -> None:
        self.factory = APIRequestFactory()
        self.user_data: dict[str, str] = TestFixtures.get_test_user_data()
        self.user: User = User.objects.create_user(
            username=self.user_data["username"],
            email=self.user_data["email"],
            password=self.user_data["password"],
        )

    def test_get_user_profile(self) -> None:
        request: Request = self.factory.get("/accounts/profile/")
        force_authenticate(request, user=self.user)
        response: Response = UserProfileView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], self.user_data["email"])

    def test_update_user_profile(self) -> None:
        update_data: dict[str, str] = {"first_name": "Updated", "last_name": "Name"}

        request: Request = self.factory.patch(
            "/accounts/profile/", update_data, format="json"
        )
        force_authenticate(request, user=self.user)
        response: Response = UserProfileView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["first_name"], "Updated")
        self.assertEqual(response.data["last_name"], "Name")

    def test_get_profile_details(self) -> None:
        request: Request = self.factory.get("/accounts/profile/details/")
        force_authenticate(request, user=self.user)
        response: Response = UserProfileDetailView.as_view()(request)

        self.assertEqual(response.status_code, 200)

    def test_update_profile_details(self) -> None:
        update_data: dict[str, str] = {
            "bio": "Test user bio for unittest",
            "organization": "Test Organization",
            "phone_number": "+48234567890",
        }

        request: Request = self.factory.patch(
            "/accounts/profile/details/", update_data, format="multipart"
        )
        force_authenticate(request, user=self.user)
        response: Response = UserProfileDetailView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["bio"], "Test user bio for unittest")
        self.assertEqual(response.data["organization"], "Test Organization")


class TestUserStats(TestCase):
    def setUp(self) -> None:
        self.factory = APIRequestFactory()
        self.user_data: dict[str, str] = TestFixtures.get_test_user_data()
        self.user: User = User.objects.create_user(
            username=self.user_data["username"],
            email=self.user_data["email"],
            password=self.user_data["password"],
        )

    def test_get_user_stats(self) -> None:
        request: Request = self.factory.get("/accounts/stats/")
        force_authenticate(request, user=self.user)
        response: Response = UserProfileStats.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertIn("total_analyses", response.data)
        self.assertIn("completed_analyses", response.data)
        self.assertIn("pending_analyses", response.data)
        self.assertIn("processing_analyses", response.data)
        self.assertIn("failed_analyses", response.data)


if __name__ == "__main__":
    success: bool = run_tests([TestAuthentication, TestUserProfile, TestUserStats])
    sys.exit(0 if success else 1)
