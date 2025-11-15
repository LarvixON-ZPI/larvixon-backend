import unittest
import sys
from tests.common import APITestCase, TestFixtures, run_tests


class TestAuthentication(APITestCase):
    """Test authentication endpoints."""

    def test_01_user_registration(self):
        """Test user registration with new data."""
        new_user_data = TestFixtures.get_test_user_data()
        response = self.make_request(
            "POST", "/accounts/register/", new_user_data, auth=False
        )

        self.assertEqual(
            response.status_code, 201, f"Registration failed: {response.text}"
        )

        data = response.json()
        self.assertIn("user", data)
        self.assertIn("access", data)
        self.assertIn("refresh", data)
        self.assertEqual(data["message"], "User registered successfully")

        print("✓ User registration successful")

    def test_02_user_login(self):
        """Test user login with existing fixture user."""
        if self.test_fixtures is None:
            self.skipTest("No test fixtures available")

        login_data = {
            "email": self.test_fixtures["user_data"]["email"],
            "password": self.test_fixtures["user_data"]["password"],
        }

        response = self.make_request("POST", "/accounts/login/", login_data, auth=False)
        self.assertEqual(response.status_code, 200, f"Login failed: {response.text}")

        data = response.json()
        self.assertIn("user", data)
        self.assertIn("access", data)
        self.assertIn("refresh", data)
        self.assertEqual(data["message"], "Login successful")

        print("✓ User login successful")

    def test_03_invalid_login(self):
        """Test login with invalid credentials."""
        if self.test_fixtures is None:
            self.skipTest("No test fixtures available")

        invalid_data = {
            "email": self.test_fixtures["user_data"]["email"],
            "password": "wrongpassword",
        }

        response = self.make_request(
            "POST", "/accounts/login/", invalid_data, auth=False
        )
        self.assertEqual(response.status_code, 400)

        print("✓ Invalid login correctly rejected")

    def test_04_duplicate_registration(self):
        """Test registration with duplicate email."""
        if self.test_fixtures is None:
            self.skipTest("No test fixtures available")

        response = self.make_request(
            "POST", "/accounts/register/", self.test_fixtures["user_data"], auth=False
        )
        self.assertEqual(response.status_code, 400)

        print("✓ Duplicate registration correctly rejected")


class TestUserProfile(APITestCase):
    """Test user profile management."""

    def test_01_get_user_profile(self):
        """Test getting user profile."""
        if self.test_fixtures is None:
            self.skipTest("No test fixtures available")

        response = self.make_request("GET", "/accounts/profile/")
        self.assertEqual(
            response.status_code, 200, f"Get profile failed: {response.text}"
        )

        data = response.json()
        self.assertEqual(data["email"], self.test_fixtures["user_data"]["email"])

        print("✓ Get user profile successful")

    def test_02_update_user_profile(self):
        """Test updating user profile."""
        if self.test_fixtures is None:
            self.skipTest("No test fixtures available")

        update_data = {"first_name": "Updated", "last_name": "Name"}

        response = self.make_request("PATCH", "/accounts/profile/", update_data)
        self.assertEqual(
            response.status_code, 200, f"Update profile failed: {response.text}"
        )

        data = response.json()
        self.assertEqual(data["first_name"], "Updated")
        self.assertEqual(data["last_name"], "Name")

        print("✓ Update user profile successful")

    def test_03_get_profile_details(self):
        """Test getting profile details."""
        if self.test_fixtures is None:
            self.skipTest("No test fixtures available")

        response = self.make_request("GET", "/accounts/profile/details/")
        self.assertEqual(
            response.status_code, 200, f"Get profile details failed: {response.text}"
        )

        print("✓ Get profile details successful")

    def test_04_update_profile_details(self):
        """Test updating profile details."""
        if self.test_fixtures is None:
            self.skipTest("No test fixtures available")

        update_data = {
            "bio": "Test user bio for unittest",
            "organization": "Test Organization",
            "phone_number": "+48234567890",
        }

        response = self.make_request("PATCH", "/accounts/profile/details/", update_data)
        self.assertEqual(
            response.status_code, 200, f"Update profile details failed: {response.text}"
        )

        data = response.json()
        self.assertEqual(data["bio"], "Test user bio for unittest")
        self.assertEqual(data["organization"], "Test Organization")

        print("✓ Update profile details successful")


class TestUserStats(APITestCase):
    """Test user statistics."""

    def test_01_get_user_stats(self):
        """Test getting user statistics."""
        if self.test_fixtures is None:
            self.skipTest("No test fixtures available")

        response = self.make_request("GET", "/accounts/stats/")
        self.assertEqual(
            response.status_code, 200, f"Get stats failed: {response.text}"
        )

        data = response.json()
        self.assertIn("total_analyses", data)
        self.assertIn("completed_analyses", data)
        self.assertIn("pending_analyses", data)
        self.assertIn("processing_analyses", data)
        self.assertIn("failed_analyses", data)

        print("✓ Get user statistics successful")


class TestJWTTokens(APITestCase):
    """Test JWT token endpoints."""

    def test_01_obtain_token(self):
        """Test token obtain endpoint."""
        if self.test_fixtures is None:
            self.skipTest("No test fixtures available")

        token_data = {
            "email": self.test_fixtures["user_data"]["email"],
            "password": self.test_fixtures["user_data"]["password"],
        }

        response = self.make_request("POST", "/token/", token_data, auth=False)
        self.assertEqual(
            response.status_code, 200, f"Token obtain failed: {response.text}"
        )

        data = response.json()
        self.assertIn("access", data)
        self.assertIn("refresh", data)

        print("✓ JWT token obtain successful")

    def test_02_verify_token(self):
        """Test token verify endpoint."""
        if self.test_fixtures is None:
            self.skipTest("No test fixtures available")

        verify_data = {"token": self.test_fixtures["access_token"]}

        response = self.make_request("POST", "/token/verify/", verify_data, auth=False)
        self.assertEqual(
            response.status_code, 200, f"Token verify failed: {response.text}"
        )

        print("✓ JWT token verify successful")


if __name__ == "__main__":
    success = run_tests(
        [TestAuthentication, TestUserProfile, TestUserStats, TestJWTTokens]
    )
    sys.exit(0 if success else 1)
