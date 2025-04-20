from django.core.management.base import BaseCommand
from items.models import Message

class Command(BaseCommand):
    help = 'Deletes all system messages from the database'

    def handle(self, *args, **options):
        # Удаляем все сообщения, которые начинаются с "Message from"
        deleted_count = Message.objects.filter(content__startswith='Message from').delete()[0]
        self.stdout.write(self.style.SUCCESS(f'Successfully deleted {deleted_count} system messages')) 