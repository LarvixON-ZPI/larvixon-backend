import unittest
import uuid
import sys
from pathlib import Path
import shutil


class TestFixtures:
    @staticmethod
    def get_test_user_data() -> dict[str, str]:
        unique_id = uuid.uuid4().hex[:8]
        return {
            "username": f"testuser_{unique_id}",
            "email": f"test_{unique_id}@example.com",
            "password": "testpass123",
            "password_confirm": "testpass123",
            "first_name": "Test",
            "last_name": "User",
        }


def cleanup_test_media():
    test_media_users = Path(__file__).parent.parent / "test_media" / "users"
    if test_media_users.exists():
        shutil.rmtree(test_media_users)


def run_tests(test_classes) -> bool:
    print("=" * 60)
    print("LARVIXON BACKEND TESTS")
    print("=" * 60)

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)

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
