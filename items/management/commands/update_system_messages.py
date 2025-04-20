from django.core.management.base import BaseCommand
from items.models import Message

class Command(BaseCommand):
    help = 'Updates existing messages to mark system messages'

    def handle(self, *args, **options):
        # Находим все сообщения, которые начинаются с 'Message from'
        system_messages = Message.objects.filter(content__startswith='Message from')
        
        # Обновляем их статус
        updated_count = system_messages.update(is_system=True)
        
        self.stdout.write(self.style.SUCCESS(f'Successfully updated {updated_count} system messages')) 