import unittest
import uuid
import requests
import time
import os
import sys
import subprocess
import sqlite3

# Add the parent directory to Python path so Django can be found
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TEST_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "test_db.sqlite3"
)

# Configuration
BASE_URL = "http://127.0.0.1:8001"
API_BASE = f"{BASE_URL}/api"
TEST_DB = "test_db.sqlite3"


class TestFixtures:
    @staticmethod
    def get_test_user_data() -> dict[str, str]:
        """Get test user data with UUID to avoid conflicts."""
        unique_id = uuid.uuid4().hex[:8]
        return {
            "username": f"testuser_{unique_id}",
            "email": f"test_{unique_id}@example.com",
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
    def __init__(self) -> None:
        self.process = None
        self.project_root = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))

    def setup_test_database(self) -> None:
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)

        os.environ['DJANGO_DB_PATH'] = TEST_DB_PATH

    def teardown_test_database(self) -> None:
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)

    def start(self):
        try:
            self.setup_test_database()

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
            self.teardown_test_database()
            return False

    def stop(self) -> None:
        if self.process:
            self.process.terminate()
            self.process.wait()


class APITestCase(unittest.TestCase):
    server = None
    test_fixtures = None
    headers: dict[str, str]

    @classmethod
    def setUpClass(cls) -> None:
        """Set up test environment - shared across all test classes."""
        if cls.server is None:
            cls.server = TestDjangoServer()
            cls.headers = {'Content-Type': 'application/json'}

            if not cls.server.start():
                raise Exception("Failed to start Django test server")

            cls.test_fixtures = TestFixtures.create_test_user(
                BASE_URL, API_BASE)
            print(
                f"Test user created: {cls.test_fixtures['user_data']['email']}")

    @classmethod
    def tearDownClass(cls) -> None:
        """Tear down test environment - only when all tests are done."""
        # This will be called for each test class, but we only want to stop once
        pass

    def make_request(self, method, endpoint, data=None, auth=True) -> requests.Response:
        url: str = f"{API_BASE}{endpoint}"
        headers: dict[str, str] = self.headers.copy()

        if auth and self.test_fixtures is not None:
            headers['Authorization'] = f'Bearer {self.test_fixtures["access_token"]}'

        try:
            response: requests.Response
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


def run_tests(test_classes) -> bool:
    print("=" * 60)
    print("LARVIXON BACKEND ACCOUNT TESTS")
    print("=" * 60)

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("=" * 60)
    if result.wasSuccessful():
        print("ALL ACCOUNT TESTS PASSED! ✓")
    else:
        print("SOME ACCOUNT TESTS FAILED! ✗")
        print(f"Failures: {len(result.failures)}")
        print(f"Errors: {len(result.errors)}")
    print("=" * 60)

    return result.wasSuccessful()
