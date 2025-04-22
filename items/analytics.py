import time
import requests
from datetime import datetime, timezone
from django.conf import settings
from django.db.models import Avg, Count, Q
from .models import Item, Message, UserProfile
from django.utils import timezone
from .amplitude_config import track_event, identify_user

def track_user_registration(user):
    """Track when a new user registers"""
    identify_user(
        user.id,
        {
            'username': user.username,
            'email': user.email,
            'date_joined': user.date_joined.isoformat(),
            'status': user.profile.status if hasattr(user, 'profile') else 'user'
        }
    )
    track_event(
        user.id,
        'user_registered',
        {
            'username': user.username,
            'email': user.email
        }
    )

def track_item_creation(item):
    """Track when a new item is created"""
    track_event(
        item.owner.id,
        'item_created',
        {
            'item_id': item.id,
            'title': item.title,
            'price': float(item.price),
            'category': item.category,
            'is_in_airhall': item.is_in_airhall
        }
    )

def track_item_view(item, user):
    """Track when an item is viewed"""
    track_event(
        user.id,
        'item_viewed',
        {
            'item_id': item.id,
            'owner_id': item.owner.id,
            'is_owner': user == item.owner,
            'price': float(item.price),
            'category': item.category,
            'is_in_airhall': item.is_in_airhall
        }
    )

def track_item_sold(item):
    """Track when an item is marked as sold"""
    track_event(
        item.owner.id,
        'item_sold',
        {
            'item_id': item.id,
            'title': item.title,
            'price': float(item.price),
            'category': item.category
        }
    )

def track_message_sent(message):
    """Track when a message is sent"""
    track_event(
        message.sender.id,
        'message_sent',
        {
            'message_id': message.id,
            'item_id': message.item.id,
            'receiver_id': message.receiver.id,
            'has_image': bool(message.image),
            'is_system': message.is_system
        }
    )

def track_first_message(item, message):
    """Track when the first message is sent about an item"""
    track_event(
        message.sender.id,
        'first_message_sent',
        {
            'item_id': item.id,
            'owner_id': item.owner.id,
            'is_owner': message.sender == item.owner
        }
    )

def track_airhall_status(item, is_in_airhall):
    """Track when an item's airhall status changes"""
    track_event(
        item.owner.id,
        'airhall_status_changed',
        {
            'item_id': item.id,
            'is_in_airhall': is_in_airhall,
            'location': item.airhall_location if is_in_airhall else None
        }
    )

def track_user_status_change(user, old_status, new_status):
    """Track when a user's status changes"""
    track_event(
        user.id,
        'user_status_changed',
        {
            'old_status': old_status,
            'new_status': new_status
        }
    )
    identify_user(
        user.id,
        {
            'status': new_status
        }
    )

def track_category_stats():
    """Track category statistics"""
    from .models import Item  # Import here to avoid circular import
    from django.db.models import Count, Avg, Q
    
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