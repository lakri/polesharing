from django.core.management.base import BaseCommand
from items.models import Message

class Command(BaseCommand):
    help = 'Cleans up all messages that match system message pattern'

    def handle(self, *args, **options):
        # Получаем все сообщения
        all_messages = Message.objects.all()
        deleted_count = 0
        
        for message in all_messages:
            # Проверяем, соответствует ли сообщение шаблону системного
            if (message.content and 
                'Message from' in message.content and 
                'to' in message.content and 
                'about' in message.content):
                message.delete()
                deleted_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Successfully deleted {deleted_count} system messages')) 