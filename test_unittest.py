#!/usr/bin/env python3
"""
Unit tests for the Larvixon Backend API using standard unittest module.
This test suite covers all account management functionality.
"""

import unittest
import json
import requests
import time
import os
import sys
import subprocess
import sqlite3
from threading import Thread
from contextlib import contextmanager

# Configuration
BASE_URL = "http://127.0.0.1:8001"  # Use different port to avoid conflicts
API_BASE = f"{BASE_URL}/api"
TEST_DB = "test_db.sqlite3"


class TestDjangoServer:
    """Helper class to manage Django test server."""

    def __init__(self):
        self.process = None

    def clear_database(self):
        """Clear the test database."""
        db_path = os.path.join(os.path.dirname(__file__), "db.sqlite3")
        if os.path.exists(db_path):
            try:
                # Connect to database and clear user-related tables
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()

                # Clear tables in correct order (due to foreign keys)
                cursor.execute("DELETE FROM accounts_videoanalysis")
                cursor.execute("DELETE FROM accounts_userprofile")
                cursor.execute(
                    "DELETE FROM auth_user WHERE email LIKE '%test%' OR username LIKE '%test%'")

                conn.commit()
                conn.close()
                print("Test database cleared successfully")
            except Exception as e:
                print(f"Warning: Could not clear database: {e}")
                # If we can't clear it, delete the file
                try:
                    os.remove(db_path)
                    print("Database file removed")
                except:
                    pass

    def start(self):
        """Start Django development server."""
        try:
            # Clear database before starting
            self.clear_database()

            # Set environment variables for testing
            os.environ['DJANGO_SETTINGS_MODULE'] = 'larvixon_site.settings'

            # Run migrations first
            migration_cmd = [
                sys.executable,
                'manage.py',
                'migrate',
                '--settings=larvixon_site.settings'
            ]

            migration_process = subprocess.run(
                migration_cmd,
                cwd=os.path.dirname(os.path.abspath(__file__)),
                capture_output=True,
                text=True
            )

            if migration_process.returncode != 0:
                print(f"Migration failed: {migration_process.stderr}")

            # Start server in a separate process
            cmd = [
                sys.executable,
                'manage.py',
                'runserver',
                '127.0.0.1:8001',
                '--settings=larvixon_site.settings'
            ]

            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )

            # Wait for server to start
            time.sleep(3)

            # Check if server is running
            try:
                response = requests.get(
                    f"{BASE_URL}/api/accounts/register/", timeout=5)
                return True
            except requests.exceptions.RequestException:
                return False

        except Exception as e:
            print(f"Failed to start server: {e}")
            return False

    def stop(self):
        """Stop Django development server."""
        if self.process:
            self.process.terminate()
            self.process.wait()


class LarvixonAPITestCase(unittest.TestCase):
    """Base test case for Larvixon API tests."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        cls.server = TestDjangoServer()
        cls.headers = {'Content-Type': 'application/json'}

        # Use timestamp to create unique test data
        import time
        timestamp = str(int(time.time()))

        cls.test_user_data = {
            "username": f"testuser_{timestamp}",
            "email": f"test_{timestamp}@example.com",
            "password": "testpass123",
            "password_confirm": "testpass123",
            "first_name": "Test",
            "last_name": "User"
        }
        cls.access_token = None
        cls.user_id = None

        # Start server
        print("Starting Django test server...")
        if not cls.server.start():
            raise Exception("Failed to start Django test server")
        print("Django test server started successfully")

    @classmethod
    def tearDownClass(cls):
        """Tear down test environment."""
        print("Stopping Django test server...")
        cls.server.stop()
        print("Django test server stopped")

    def make_request(self, method, endpoint, data=None, auth=True):
        """Make HTTP request to API."""
        url = f"{API_BASE}{endpoint}"
        headers = self.headers.copy()

        if auth and self.access_token:
            headers['Authorization'] = f'Bearer {self.access_token}'

        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method.upper() == 'POST':
                response = requests.post(
                    url, json=data, headers=headers, timeout=10)
            elif method.upper() == 'PATCH':
                response = requests.patch(
                    url, json=data, headers=headers, timeout=10)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            return response

        except requests.exceptions.RequestException as e:
            self.fail(f"Request failed: {e}")


class TestAuthentication(LarvixonAPITestCase):
    """Test authentication endpoints."""

    def test_01_user_registration(self):
        """Test user registration."""
        response = self.make_request(
            'POST', '/accounts/register/', self.test_user_data, auth=False)

        self.assertEqual(response.status_code, 201,
                         f"Registration failed: {response.text}")

        data = response.json()
        self.assertIn('user', data)
        self.assertIn('access', data)
        self.assertIn('refresh', data)
        self.assertEqual(data['message'], 'User registered successfully')

        # Store token and user ID for subsequent tests
        self.__class__.access_token = data['access']
        self.__class__.user_id = data['user']['id']

        print("✓ User registration successful")

    def test_02_user_login(self):
        """Test user login."""
        login_data = {
            "email": self.test_user_data['email'],
            "password": self.test_user_data['password']
        }

        response = self.make_request(
            'POST', '/accounts/login/', login_data, auth=False)
        self.assertEqual(response.status_code, 200,
                         f"Login failed: {response.text}")

        data = response.json()
        self.assertIn('user', data)
        self.assertIn('access', data)
        self.assertIn('refresh', data)
        self.assertEqual(data['message'], 'Login successful')

        print("✓ User login successful")

    def test_03_invalid_login(self):
        """Test login with invalid credentials."""
        invalid_data = {
            "email": self.test_user_data['email'],
            "password": "wrongpassword"
        }

        response = self.make_request(
            'POST', '/accounts/login/', invalid_data, auth=False)
        self.assertEqual(response.status_code, 400)

        print("✓ Invalid login correctly rejected")

    def test_04_duplicate_registration(self):
        """Test registration with duplicate email."""
        response = self.make_request(
            'POST', '/accounts/register/', self.test_user_data, auth=False)
        self.assertEqual(response.status_code, 400)

        print("✓ Duplicate registration correctly rejected")


class TestUserProfile(LarvixonAPITestCase):
    """Test user profile management."""

    def test_01_get_user_profile(self):
        """Test getting user profile."""
        if not self.access_token:
            self.skipTest("No access token available")

        response = self.make_request('GET', '/accounts/profile/')
        self.assertEqual(response.status_code, 200,
                         f"Get profile failed: {response.text}")

        data = response.json()
        self.assertEqual(data['email'], self.test_user_data['email'])

        print("✓ Get user profile successful")

    def test_02_update_user_profile(self):
        """Test updating user profile."""
        if not self.access_token:
            self.skipTest("No access token available")

        update_data = {
            "first_name": "Updated",
            "last_name": "Name"
        }

        response = self.make_request(
            'PATCH', '/accounts/profile/', update_data)
        self.assertEqual(response.status_code, 200,
                         f"Update profile failed: {response.text}")

        data = response.json()
        self.assertEqual(data['first_name'], 'Updated')
        self.assertEqual(data['last_name'], 'Name')

        print("✓ Update user profile successful")

    def test_03_get_profile_details(self):
        """Test getting profile details."""
        if not self.access_token:
            self.skipTest("No access token available")

        response = self.make_request('GET', '/accounts/profile/details/')
        self.assertEqual(response.status_code, 200,
                         f"Get profile details failed: {response.text}")

        print("✓ Get profile details successful")

    def test_04_update_profile_details(self):
        """Test updating profile details."""
        if not self.access_token:
            self.skipTest("No access token available")

        update_data = {
            "bio": "Test user bio for unittest",
            "organization": "Test Organization",
            "phone_number": "+1234567890"
        }

        response = self.make_request(
            'PATCH', '/accounts/profile/details/', update_data)
        self.assertEqual(response.status_code, 200,
                         f"Update profile details failed: {response.text}")

        data = response.json()
        self.assertEqual(data['bio'], 'Test user bio for unittest')
        self.assertEqual(data['organization'], 'Test Organization')

        print("✓ Update profile details successful")


class TestVideoAnalysis(LarvixonAPITestCase):
    """Test video analysis management."""

    def setUp(self):
        """Set up for video analysis tests."""
        self.analysis_id = None

    def test_01_create_analysis(self):
        """Test creating video analysis."""
        if not self.access_token:
            self.skipTest("No access token available")

        create_data = {
            "video_name": "test_video_unittest.mp4",
            "video_file_path": "/uploads/test_video_unittest.mp4"
        }

        response = self.make_request(
            'POST', '/accounts/analyses/', create_data)
        self.assertEqual(response.status_code, 201,
                         f"Create analysis failed: {response.text}")

        data = response.json()
        self.assertEqual(data['video_name'], 'test_video_unittest.mp4')
        self.assertEqual(data['status'], 'pending')

        self.analysis_id = data['id']
        print("✓ Create video analysis successful")

    def test_02_get_analyses_list(self):
        """Test getting analyses list."""
        if not self.access_token:
            self.skipTest("No access token available")

        response = self.make_request('GET', '/accounts/analyses/')
        self.assertEqual(response.status_code, 200,
                         f"Get analyses failed: {response.text}")

        data = response.json()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)

        print("✓ Get analyses list successful")

    def test_03_update_analysis_feedback(self):
        """Test updating analysis with feedback."""
        if not self.access_token:
            self.skipTest("No access token available")

        # First create an analysis
        create_data = {
            "video_name": "feedback_test.mp4",
            "video_file_path": "/uploads/feedback_test.mp4"
        }

        response = self.make_request(
            'POST', '/accounts/analyses/', create_data)
        self.assertEqual(response.status_code, 201)
        analysis_id = response.json()['id']

        # Update with feedback
        update_data = {
            "actual_substance": "cocaine",
            "user_feedback": "This is unittest feedback"
        }

        response = self.make_request(
            'PATCH', f'/accounts/analyses/{analysis_id}/', update_data)
        self.assertEqual(response.status_code, 200,
                         f"Update feedback failed: {response.text}")

        data = response.json()
        self.assertEqual(data['actual_substance'], 'cocaine')
        self.assertEqual(data['user_feedback'], 'This is unittest feedback')

        print("✓ Update analysis feedback successful")


class TestUserStats(LarvixonAPITestCase):
    """Test user statistics."""

    def test_01_get_user_stats(self):
        """Test getting user statistics."""
        if not self.access_token:
            self.skipTest("No access token available")

        response = self.make_request('GET', '/accounts/stats/')
        self.assertEqual(response.status_code, 200,
                         f"Get stats failed: {response.text}")

        data = response.json()
        self.assertIn('total_analyses', data)
        self.assertIn('completed_analyses', data)
        self.assertIn('pending_analyses', data)
        self.assertIn('processing_analyses', data)
        self.assertIn('failed_analyses', data)

        # Should have at least 2 analyses from previous tests
        self.assertGreaterEqual(data['total_analyses'], 2)

        print("✓ Get user statistics successful")


class TestJWTTokens(LarvixonAPITestCase):
    """Test JWT token endpoints."""

    def test_01_obtain_token(self):
        """Test token obtain endpoint."""
        token_data = {
            "email": self.test_user_data['email'],
            "password": self.test_user_data['password']
        }

        response = self.make_request('POST', '/token/', token_data, auth=False)
        self.assertEqual(response.status_code, 200,
                         f"Token obtain failed: {response.text}")

        data = response.json()
        self.assertIn('access', data)
        self.assertIn('refresh', data)

        print("✓ JWT token obtain successful")

    def test_02_verify_token(self):
        """Test token verify endpoint."""
        if not self.access_token:
            self.skipTest("No access token available")

        verify_data = {
            "token": self.access_token
        }

        response = self.make_request(
            'POST', '/token/verify/', verify_data, auth=False)
        self.assertEqual(response.status_code, 200,
                         f"Token verify failed: {response.text}")

        print("✓ JWT token verify successful")


def run_tests():
    """Run all test suites."""
    print("=" * 60)
    print("LARVIXON BACKEND UNITTEST SUITE")
    print("=" * 60)

    # Create test loader and suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test classes in order
    test_classes = [
        TestAuthentication,
        TestUserProfile,
        TestVideoAnalysis,
        TestUserStats,
        TestJWTTokens
    ]

    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("=" * 60)
    if result.wasSuccessful():
        print("ALL TESTS PASSED! ✓")
    else:
        print("SOME TESTS FAILED! ✗")
        print(f"Failures: {len(result.failures)}")
        print(f"Errors: {len(result.errors)}")
    print("=" * 60)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
