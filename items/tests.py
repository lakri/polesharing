from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Item, Message
from django.core.files.uploadedfile import SimpleUploadedFile
import os
from django.conf import settings

class MessageTests(TestCase):
    def setUp(self):
        # Create test users
        self.seller = User.objects.create_user(username='seller', password='testpass123')
        self.buyer1 = User.objects.create_user(username='buyer1', password='testpass123')
        self.buyer2 = User.objects.create_user(username='buyer2', password='testpass123')
        
        # Create test item
        self.item = Item.objects.create(
            title='Test Item',
            description='Test Description',
            price=100,
            owner=self.seller
        )
        
        # Create test messages
        self.message1 = Message.objects.create(
            item=self.item,
            sender=self.buyer1,
            receiver=self.seller,
            content='Message from buyer1 to seller'
        )
        
        self.message2 = Message.objects.create(
            item=self.item,
            sender=self.seller,
            receiver=self.buyer1,
            content='Reply from seller to buyer1'
        )
        
        self.message3 = Message.objects.create(
            item=self.item,
            sender=self.buyer2,
            receiver=self.seller,
            content='Message from buyer2 to seller'
        )
        
        # Create test client
        self.client = Client()

    def test_message_creation(self):
        """Test that messages are created correctly"""
        self.assertEqual(Message.objects.count(), 3)
        self.assertEqual(self.message1.sender, self.buyer1)
        self.assertEqual(self.message1.receiver, self.seller)
        self.assertEqual(self.message1.item, self.item)

    def test_seller_sees_messages(self):
        """Test that seller sees messages"""
        self.client.login(username='seller', password='testpass123')
        response = self.client.get(reverse('item_detail', args=[self.item.pk]))
        
        # Should see messages with buyer2 (last buyer)
        self.assertContains(response, 'Message from buyer2 to seller')
        self.assertNotContains(response, 'Message from buyer1 to seller')
        self.assertNotContains(response, 'Reply from seller to buyer1')

    def test_buyer_sees_messages(self):
        """Test that buyer sees messages"""
        self.client.login(username='buyer1', password='testpass123')
        response = self.client.get(reverse('item_detail', args=[self.item.pk]))
        
        # Should see only messages with seller
        self.assertContains(response, 'Message from buyer1 to seller')
        self.assertContains(response, 'Reply from seller to buyer1')
        self.assertNotContains(response, 'Message from buyer2 to seller')

    def test_my_messages_view_for_seller(self):
        """Test my_messages view for seller"""
        self.client.login(username='seller', password='testpass123')
        response = self.client.get(reverse('my_messages'))
        
        # Should see conversation with buyer2 (last buyer)
        self.assertContains(response, 'Test Item')
        self.assertContains(response, 'buyer2')
        self.assertNotContains(response, 'buyer1')

    def test_my_messages_view_for_buyer(self):
        """Test my_messages view for buyer"""
        self.client.login(username='buyer1', password='testpass123')
        response = self.client.get(reverse('my_messages'))
        
        # Should see conversation with seller
        self.assertContains(response, 'Test Item')
        self.assertContains(response, 'seller')

    def test_send_message_as_buyer(self):
        """Test sending message as buyer"""
        self.client.login(username='buyer1', password='testpass123')
        response = self.client.post(
            reverse('item_detail', args=[self.item.pk]),
            {'content': 'New message from buyer1'}
        )
        
        # Check if message was created
        self.assertEqual(Message.objects.count(), 4)
        new_message = Message.objects.latest('created_at')
        self.assertEqual(new_message.sender, self.buyer1)
        self.assertEqual(new_message.receiver, self.seller)
        self.assertEqual(new_message.content, 'New message from buyer1')

    def test_send_message_as_seller(self):
        """Test sending message as seller"""
        self.client.login(username='seller', password='testpass123')
        response = self.client.post(
            reverse('item_detail', args=[self.item.pk]),
            {'content': 'New message from seller'}
        )
        
        # Check if message was created
        self.assertEqual(Message.objects.count(), 4)
        new_message = Message.objects.latest('created_at')
        self.assertEqual(new_message.sender, self.seller)
        self.assertEqual(new_message.receiver, self.buyer1)  # Messages are sent to buyer1
        self.assertEqual(new_message.content, 'New message from seller')

    def test_unauthenticated_user_cannot_send_messages(self):
        """Test that unauthenticated users cannot send messages"""
        response = self.client.post(
            reverse('item_detail', args=[self.item.pk]),
            {'content': 'Unauthenticated message'}
        )
        
        # Should redirect to login
        self.assertRedirects(response, f'/login/?next=/item/{self.item.pk}/')
        self.assertEqual(Message.objects.count(), 3)  # No new messages created

    def test_message_ordering(self):
        """Test that messages are ordered by creation time"""
        messages = Message.objects.filter(item=self.item).order_by('created_at')
        self.assertEqual(messages[0], self.message1)
        self.assertEqual(messages[1], self.message2)
        self.assertEqual(messages[2], self.message3)
