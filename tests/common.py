import unittest
import requests
import time
import os
import sys
import subprocess
import sqlite3

# Add the parent directory to Python path so Django can be found
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuration
BASE_URL = "http://127.0.0.1:8001"  # Use different port to avoid conflicts
API_BASE = f"{BASE_URL}/api"
TEST_DB = "test_db.sqlite3"


class TestFixtures:
    """Helper class to manage test data and fixtures."""

    @staticmethod
    def get_test_user_data() -> dict[str, str]:
        """Get test user data with timestamp to avoid conflicts."""
        timestamp = str(int(time.time()))
        return {
            "username": f"testuser_{timestamp}",
            "email": f"test_{timestamp}@example.com",
            "password": "testpass123",
            "password_confirm": "testpass123",
            "first_name": "Test",
            "last_name": "User"
        }

    @staticmethod
    def create_test_user(base_url, api_base):
        """Create a test user and return user data with tokens."""
        test_user_data = TestFixtures.get_test_user_data()

        # Register user
        response = requests.post(
            f"{api_base}/accounts/register/",
            json=test_user_data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )

        if response.status_code == 201:
            data = response.json()
            return {
                'user_data': test_user_data,
                'access_token': data['access'],
                'refresh_token': data['refresh'],
                'user_id': data['user']['id']
            }
        else:
            raise Exception(f"Failed to create test user: {response.text}")


class TestDjangoServer:
    """Helper class to manage Django test server."""

    def __init__(self) -> None:
        self.process = None
        # Set the project root directory (parent of tests folder)
        self.project_root = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))

    def clear_database(self) -> None:
        """Clear the test database."""
        db_path: str = os.path.join(self.project_root, "db.sqlite3")
        if os.path.exists(db_path):
            try:
                connection: sqlite3.Connection = sqlite3.connect(db_path)
                cursor: sqlite3.Cursor = connection.cursor()

                cursor.execute("DELETE FROM accounts_videoanalysis")
                cursor.execute("DELETE FROM accounts_userprofile")
                cursor.execute(
                    "DELETE FROM auth_user WHERE email LIKE '%test%' OR username LIKE '%test%'")

                connection.commit()
                connection.close()
                print("Test database cleared successfully")
            except Exception as e:
                print(f"Warning: Could not clear database: {e}")
                try:
                    os.remove(db_path)
                    print("Database file removed")
                except:
                    pass

    def start(self):
        """Start Django development server."""
        try:
            self.clear_database()

            os.environ['DJANGO_SETTINGS_MODULE'] = 'larvixon_site.settings'

            # Run migrations first - use project root as cwd
            migration_cmd = [
                sys.executable,
                'manage.py',
                'migrate',
                '--settings=larvixon_site.settings'
            ]

            migration_process = subprocess.run(
                migration_cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True
            )

            if migration_process.returncode != 0:
                print(f"Migration failed: {migration_process.stderr}")

            # Start server in a separate process - use project root as cwd
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
                cwd=self.project_root
            )

            # Wait for server to start
            time.sleep(3)

            # Check if server is running
            try:
                requests.get(
                    f"{BASE_URL}/api/accounts/register/", timeout=5)
                return True
            except requests.exceptions.RequestException:
                return False

        except Exception as e:
            print(f"Failed to start server: {e}")
            return False

    def stop(self) -> None:
        """Stop Django development server."""
        if self.process:
            self.process.terminate()
            self.process.wait()


class LarvixonAPITestCase(unittest.TestCase):
    """Base test case for Larvixon API tests."""

    server = None
    test_fixtures = None

    @classmethod
    def setUpClass(cls):
        """Set up test environment - shared across all test classes."""
        if cls.server is None:
            cls.server = TestDjangoServer()
            cls.headers = {'Content-Type': 'application/json'}

            # Start server
            print("Starting Django test server...")
            if not cls.server.start():
                raise Exception("Failed to start Django test server")
            print("Django test server started successfully")

            # Create test fixtures
            cls.test_fixtures = TestFixtures.create_test_user(
                BASE_URL, API_BASE)
            print(
                f"Test user created: {cls.test_fixtures['user_data']['email']}")

    @classmethod
    def tearDownClass(cls):
        """Tear down test environment - only when all tests are done."""
        # This will be called for each test class, but we only want to stop once
        pass

    def make_request(self, method, endpoint, data=None, auth=True):
        """Make HTTP request to API."""
        url = f"{API_BASE}{endpoint}"
        headers = self.headers.copy()

        if auth and self.test_fixtures is not None:
            headers['Authorization'] = f'Bearer {self.test_fixtures["access_token"]}'

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
