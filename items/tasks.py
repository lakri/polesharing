from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .models import Message

def check_unread_messages():
    # Получаем все непрочитанные сообщения
    unread_messages = Message.objects.filter(is_read=False)
    
    # Группируем сообщения по получателю
    messages_by_user = {}
    for message in unread_messages:
        if message.receiver.email not in messages_by_user:
            messages_by_user[message.receiver.email] = []
        messages_by_user[message.receiver.email].append(message)
    
    # Отправляем уведомления каждому пользователю
    for email, messages in messages_by_user.items():
        context = {
            'messages': messages,
            'unread_count': len(messages),
        }
        
        # Рендерим HTML шаблон для email
        html_message = render_to_string('items/email/unread_messages.html', context)
        
        # Отправляем email
        send_mail(
            subject='У вас есть непрочитанные сообщения',
            message='',
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email],
            html_message=html_message,
        ) 