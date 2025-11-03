import requests
import json
import os
from typing import Dict, Optional
from larvixon_site.settings import ML_ENDPOINT_URL


def send_video_to_ml(video_path: str) -> Optional[Dict[str, float]]:
    """
    Sends a video file as multipart/form-data to the external ML endpoint
    and returns a dictionary of predictions with confidence scores.
    """

    if not os.path.exists(video_path):
        print(f"Error: Video file not found at {video_path}")
        return None

    try:
        with open(video_path, "rb") as video_file:
            files = {"file": (os.path.basename(video_path), video_file, "video/webm")}
            headers = {"Accept": "application/json"}

            print(f"Sending request to ML endpoint: {ML_ENDPOINT_URL}")
            response = requests.post(ML_ENDPOINT_URL, headers=headers, files=files)

        if response.status_code != 200:
            print(
                f"ML endpoint request failed ({response.status_code}): {response.text}"
            )
            return None

        try:
            data = response.json()
        except json.JSONDecodeError:
            print(f"Error: Failed to decode JSON response: {response.text}")
            return None

        raw_scores = data.get("predictions")
        if not raw_scores:
            print("ML endpoint response missing 'predictions' key.")
            return None

        return {k: float(v) for k, v in raw_scores.items()}

    except requests.exceptions.RequestException as e:
        print(f"Request to ML endpoint failed: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None
