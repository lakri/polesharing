import requests
import json
import time
import os

AMPLITUDE_API_URL = "https://api2.amplitude.com/2/httpapi"
AMPLITUDE_API_KEY = os.getenv('AMPLITUDE_API_KEY')

def track_event(user_id, event_type, event_properties=None):
    """
    Track an event in Amplitude
    
    Args:
        user_id: The ID of the user performing the action
        event_type: The type of event (e.g., 'item_viewed', 'message_sent')
        event_properties: Dictionary of additional properties for the event
    """
    try:
        # Ensure user_id is a string and not empty
        if not user_id:
            user_id = "anonymous"
        user_id = str(user_id)
        
        # Create event data
        event_data = {
            "api_key": AMPLITUDE_API_KEY,
            "events": [{
                "user_id": user_id,
                "device_id": user_id,  # Add device_id to ensure proper identification
                "event_type": event_type,
                "event_properties": event_properties or {},
                "time": int(time.time() * 1000)  # Current time in milliseconds
            }]
        }
        
        # Send event
        response = requests.post(AMPLITUDE_API_URL, json=event_data)
        if response.status_code == 200:
            print(f"Event tracked successfully: {event_type}")
        else:
            print(f"Error tracking event. Status code: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error tracking event in Amplitude: {str(e)}")

def identify_user(user_id, user_properties):
    """
    Identify a user in Amplitude with their properties
    
    Args:
        user_id: The ID of the user
        user_properties: Dictionary of user properties
    """
    try:
        # Ensure user_id is a string and not empty
        if not user_id:
            user_id = "anonymous"
        user_id = str(user_id)
        
        # For user identification, we'll use the same endpoint but with a special event type
        event_data = {
            "api_key": AMPLITUDE_API_KEY,
            "events": [{
                "user_id": user_id,
                "device_id": user_id,  # Add device_id to ensure proper identification
                "event_type": "$identify",
                "user_properties": user_properties,
                "time": int(time.time() * 1000)  # Current time in milliseconds
            }]
        }
        
        # Send identify event
        response = requests.post(AMPLITUDE_API_URL, json=event_data)
        if response.status_code == 200:
            print(f"User identified successfully: {user_id}")
        else:
            print(f"Error identifying user. Status code: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error identifying user in Amplitude: {str(e)}") 