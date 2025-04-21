import time
import requests
from datetime import datetime, timezone
from django.conf import settings
from django.db.models import Avg, Count, Q
from .models import Item, Message
from django.utils import timezone

def track_event(event_name, properties=None, user_id=None):
    """Send event to Amplitude"""
    api_key = getattr(settings, 'AMPLITUDE_API_KEY', None)
    if not api_key or api_key == 'YOUR_API_KEY_HERE':
        # If API key is not configured, just log the event
        print(f"Analytics event (not sent): {event_name}")
        return

    amplitude_url = "https://api2.amplitude.com/2/httpapi"
    
    data = {
        "api_key": api_key,
        "events": [{
            "user_id": str(user_id) if user_id else None,
            "event_type": event_name,
            "event_properties": properties or {},
            "time": int(time.time() * 1000)
        }]
    }
    
    try:
        requests.post(amplitude_url, json=data)
    except Exception as e:
        print(f"Error sending analytics event: {e}")

def track_user_registration(user):
    """Track user registration"""
    track_event('user_registered', {
        'username': user.username,
        'registration_date': user.date_joined.isoformat(),
        'email': user.email
    }, user.id)

def track_item_creation(item):
    """Track item creation"""
    track_event('item_created', {
        'item_id': item.id,
        'title': item.title,
        'price': str(item.price),
        'category': item.category,
        'creation_date': item.created_at.isoformat(),
        'seller_id': item.owner.id,
        'seller_username': item.owner.username
    }, item.owner.id)

def track_item_sold(item):
    """Track item sale"""
    try:
        # Calculate time to sale
        time_to_sell = timezone.now() - item.created_at
        
        # Send event to Amplitude
        track_event(
            event_name='item_sold',
            user_id=str(item.owner.id),
            properties={
                'item_id': item.id,
                'title': item.title,
                'price': float(item.price),
                'category': item.category,
                'time_to_sell_days': time_to_sell.days,
                'time_to_sell_hours': time_to_sell.seconds // 3600,
                'is_in_airhall': item.is_in_airhall,
                'has_airhall_image': bool(item.airhall_image),
                'has_airhall_location': bool(item.airhall_location)
            }
        )
    except Exception as e:
        print(f"Error tracking item sold: {str(e)}")

def track_first_message(item, message):
    """Track first message for an item"""
    creation_date = item.created_at
    message_date = message.created_at
    time_to_first_message = (message_date - creation_date).total_seconds() / 3600  # in hours
    
    track_event('first_message_received', {
        'item_id': item.id,
        'title': item.title,
        'time_to_first_message_hours': time_to_first_message,
        'message_sender_id': message.sender.id,
        'message_sender_username': message.sender.username,
        'seller_id': item.owner.id,
        'seller_username': item.owner.username
    }, item.owner.id)

def track_airhall_status(item, is_in_airhall):
    """Track airhall status change"""
    track_event('airhall_status_changed', {
        'item_id': item.id,
        'title': item.title,
        'is_in_airhall': is_in_airhall,
        'change_date': datetime.now().isoformat(),
        'seller_id': item.owner.id,
        'seller_username': item.owner.username
    }, item.owner.id)

def track_item_view(item, user):
    """Track item view"""
    track_event('item_viewed', {
        'item_id': item.id,
        'title': item.title,
        'price': str(item.price),
        'category': item.category,
        'seller_id': item.owner.id,
        'seller_username': item.owner.username,
        'viewer_id': user.id if user.is_authenticated else None,
        'viewer_username': user.username if user.is_authenticated else 'anonymous'
    }, user.id if user.is_authenticated else None)

def track_message_sent(message):
    """
    Track when a message is sent
    """
    properties = {
        'item_id': message.item.id,
        'item_title': message.item.title,
        'sender_id': message.sender.id,
        'receiver_id': message.receiver.id if message.receiver else None,
        'message_length': len(message.content),
        'has_image': bool(message.image)
    }
    
    track_event('message_sent', properties, message.sender.id)

def track_category_stats():
    """Track category statistics"""
    category_stats = Item.objects.values('category').annotate(
        total_items=Count('id'),
        avg_price=Avg('price'),
        total_views=Count('views'),
        total_sold=Count('id', filter=Q(is_sold=True))
    )
    
    for stat in category_stats:
        track_event('category_stats', {
            'category': stat['category'],
            'total_items': stat['total_items'],
            'avg_price': float(stat['avg_price']) if stat['avg_price'] else 0,
            'total_views': stat['total_views'],
            'total_sold': stat['total_sold'],
            'conversion_rate': stat['total_sold'] / stat['total_views'] if stat['total_views'] > 0 else 0
        }) 