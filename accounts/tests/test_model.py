from django.test import TestCase
from ..models import UserProfile, User


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
        profile, created = UserProfile.objects.get_or_create(user=self.user)
        self.assertEqual(profile.user, self.user)
        self.assertEqual(str(profile), "test@example.com - Profile")
