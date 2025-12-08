import requests
import json
import os
import logging
from larvixon_site.settings import ML_ENDPOINT_URL
from videoprocessor.services.base_ml_service import BaseMLService

logger: logging.Logger = logging.getLogger(__name__)


class APIMLService(BaseMLService):
    @staticmethod
    def predict_video(video_path: str) -> dict[str, float] | None:
        if not os.path.exists(video_path):
            logger.error(f"Video file not found at {video_path}")
            return None

        try:
            with open(video_path, "rb") as video_file:
                files = {
                    "file": (os.path.basename(video_path), video_file, "video/webm")
                }
                headers: dict[str, str] = {"Accept": "application/json"}

                logger.info(f"Sending request to ML endpoint: {ML_ENDPOINT_URL}")
                response: requests.Response = requests.post(
                    ML_ENDPOINT_URL, headers=headers, files=files
                )

            if response.status_code != 200:
                logger.error(
                    f"ML endpoint request failed ({response.status_code}): {response.text}"
                )
                return None

            try:
                data = response.json()
            except json.JSONDecodeError:
                logger.error(f"Failed to decode JSON response: {response.text}")
                return None

            raw_scores = data.get("predictions")
            if not raw_scores:
                logger.error("ML endpoint response missing 'predictions' key.")
                return None

            logger.info(f"ML prediction successful for {video_path}")
            return {k: float(v) for k, v in raw_scores.items()}

        except requests.exceptions.RequestException as e:
            logger.error(f"Request to ML endpoint failed: {e}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error while sending video to ML: {e}")
            return None
