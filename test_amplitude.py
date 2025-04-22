import os
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from items.amplitude_config import track_event, identify_user

def test_amplitude():
    # Print current API key (masked)
    api_key = os.getenv('AMPLITUDE_API_KEY', 'not-found')
    masked_key = api_key[:4] + '*' * (len(api_key) - 8) + api_key[-4:] if len(api_key) > 8 else 'not-found'
    print(f"Using Amplitude API key: {masked_key}")

    # Test user identification
    print("\nTesting user identification...")
    identify_user(
        "test_user_123",
        {
            "username": "test_user",
            "email": "test@example.com",
            "status": "user"
        }
    )
    
    # Wait a second before sending the next event
    time.sleep(1)
    
    # Test event tracking
    print("\nTesting event tracking...")
    track_event(
        "test_user_123",
        "test_event",
        {
            "test_property": "test_value",
            "number": 42
        }
    )

if __name__ == "__main__":
    test_amplitude()
    print("\nTest completed! Check your Amplitude dashboard to verify the events were received.") 