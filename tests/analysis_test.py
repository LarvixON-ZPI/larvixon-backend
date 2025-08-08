import unittest
import sys
from common import APITestCase, run_tests


class TestVideoAnalysis(APITestCase):
    """Test video analysis management."""

    def setUp(self):
        """Set up for video analysis tests."""
        self.analysis_id = None

    def test_01_create_analysis(self):
        """Test creating video analysis."""
        if self.test_fixtures is None:
            self.skipTest("No test fixtures available")

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
        if self.test_fixtures is None:
            self.skipTest("No test fixtures available")

        response = self.make_request('GET', '/accounts/analyses/')
        self.assertEqual(response.status_code, 200,
                         f"Get analyses failed: {response.text}")

        data = response.json()
        self.assertIsInstance(data, list)

        print("✓ Get analyses list successful")

    def test_03_update_analysis_feedback(self):
        """Test updating analysis with feedback."""
        if self.test_fixtures is None:
            self.skipTest("No test fixtures available")

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


if __name__ == '__main__':
    success = run_tests([TestVideoAnalysis])
    sys.exit(0 if success else 1)
