import requests
import json
import os
from typing import Dict, Optional

ML_ENDPOINT_URL = "http://127.0.0.1:8001/predict" # when ml model is running locally at uvicorn app:app --host=0.0.0.0 --port=8001

def send_video_to_ml(video_path: str) -> Optional[Dict[str, float]]:
    """
    Sends a video file as multipart/form-data to the external ML endpoint 
    and returns a dictionary of predictions with confidence scores.
    """
    try:
        with open(video_path, 'rb') as video_file:
            files = {
                'file': (os.path.basename(video_path), video_file, 'video/webm')
            }
            
            headers = {
                'Accept': 'application/json',
            }

            print(f"Sending request to ML endpoint: {ML_ENDPOINT_URL}")
            response = requests.post(
                ML_ENDPOINT_URL, 
                headers=headers, 
                files=files
            )
            
            if response.status_code == 200:
                data = response.json()
                raw_scores = data.get("predictions")
                
                if raw_scores:
                    return {k: float(v) for k, v in raw_scores.items()}
                else:
                    print("ML endpoint response missing 'predictions' key.")
                    return None
            else:
                print(f"ML endpoint request failed with status code {response.status_code}. Response: {response.text}")
                return None
                
    except FileNotFoundError:
        print(f"Error: Video file not found at {video_path}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while connecting to the ML endpoint: {e}")
        return None
    except json.JSONDecodeError:
        print(f"Error: Failed to decode JSON response from ML endpoint. Response: {response.text}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None