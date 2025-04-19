import os
from celery import Celery
from celery.schedules import crontab

# Устанавливаем переменную окружения для настроек Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'polesharing.settings')

# Создаем экземпляр приложения Celery
app = Celery('polesharing')

# Загружаем конфигурацию из настроек Django
app.config_from_object('django.conf:settings', namespace='CELERY')

# Автоматически находим и регистрируем задачи из всех приложений Django
app.autodiscover_tasks()

# Настраиваем периодические задачи
app.conf.beat_schedule = {
    'check-unread-messages': {
        'task': 'items.tasks.check_unread_messages',
        'schedule': crontab(minute='*/15'),  # Запускать каждые 15 минут
    },
} 