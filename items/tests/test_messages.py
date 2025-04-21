from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from items.models import Item, Message
from items.forms import MessageForm

class MessageTests(TestCase):
    def setUp(self):
        # Создаем тестовых пользователей
        self.seller = User.objects.create_user(
            username='seller',
            password='testpass123'
        )
        self.buyer = User.objects.create_user(
            username='buyer',
            password='testpass123'
        )
        
        # Создаем тестовый товар
        self.item = Item.objects.create(
            title='Test Item',
            description='Test Description',
            price=100,
            owner=self.seller
        )
        
        # Создаем клиент для тестирования
        self.client = Client()

    def test_seller_can_send_message_without_previous_messages(self):
        """Проверяем, что продавец может отправить сообщение без предыдущих сообщений"""
        # Логинимся как продавец
        self.client.login(username='seller', password='testpass123')
        
        # Отправляем сообщение
        response = self.client.post(
            reverse('item_detail', args=[self.item.pk]),
            {
                'content': 'Test message from seller',
            }
        )
        
        # Проверяем, что сообщение создано
        self.assertEqual(Message.objects.count(), 1)
        message = Message.objects.first()
        self.assertEqual(message.sender, self.seller)
        self.assertIsNone(message.receiver)
        self.assertEqual(message.content, 'Test message from seller')
        
        # Проверяем редирект
        self.assertRedirects(response, reverse('item_detail', args=[self.item.pk]))

    def test_seller_can_send_message_after_buyer_message(self):
        """Проверяем, что продавец может отправить сообщение после сообщения от покупателя"""
        # Создаем сообщение от покупателя
        Message.objects.create(
            item=self.item,
            sender=self.buyer,
            receiver=self.seller,
            content='Test message from buyer'
        )
        
        # Логинимся как продавец
        self.client.login(username='seller', password='testpass123')
        
        # Отправляем сообщение
        response = self.client.post(
            reverse('item_detail', args=[self.item.pk]),
            {
                'content': 'Test reply from seller',
            }
        )
        
        # Проверяем, что сообщение создано
        self.assertEqual(Message.objects.count(), 2)
        message = Message.objects.latest('created_at')
        self.assertEqual(message.sender, self.seller)
        self.assertEqual(message.receiver, self.buyer)
        self.assertEqual(message.content, 'Test reply from seller')
        
        # Проверяем редирект
        self.assertRedirects(response, reverse('item_detail', args=[self.item.pk]))

    def test_seller_can_see_all_messages(self):
        """Проверяем, что продавец видит все сообщения"""
        # Создаем сообщения
        Message.objects.create(
            item=self.item,
            sender=self.seller,
            receiver=None,
            content='System message'
        )
        Message.objects.create(
            item=self.item,
            sender=self.buyer,
            receiver=self.seller,
            content='Buyer message'
        )
        Message.objects.create(
            item=self.item,
            sender=self.seller,
            receiver=self.buyer,
            content='Seller reply'
        )
        
        # Логинимся как продавец
        self.client.login(username='seller', password='testpass123')
        
        # Получаем страницу товара
        response = self.client.get(reverse('item_detail', args=[self.item.pk]))
        
        # Проверяем, что все сообщения отображаются
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['messages']), 3)
        
        # Проверяем содержимое сообщений
        messages = list(response.context['messages'])
        self.assertEqual(messages[0].content, 'System message')
        self.assertEqual(messages[1].content, 'Buyer message')
        self.assertEqual(messages[2].content, 'Seller reply') 