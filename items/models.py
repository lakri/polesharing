from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from PIL import Image
import pillow_heif
import os
from django.core.exceptions import ValidationError
from django.db.models import Q

CATEGORY_CHOICES = [
    ('clothes', 'Одежда'),
    ('shoes', 'Обувь'),
    ('grip', 'Средства для сцепления'),
    ('other', 'Другое')
]

class Item(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    image = models.ImageField(upload_to='items/', null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    is_sold = models.BooleanField(default=False)
    is_in_airhall = models.BooleanField(default=False)
    airhall_image = models.ImageField(upload_to='airhall_items/', null=True, blank=True)
    airhall_location = models.CharField(max_length=200, null=True, blank=True)
    category = models.CharField(max_length=100, choices=CATEGORY_CHOICES, default='other')
    views = models.PositiveIntegerField(default=0)
    is_banned = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        # Если товар помечен как находящийся в airhall, проверяем наличие фотографии
        if self.is_in_airhall and not self.airhall_image:
            raise ValidationError("Для товара в airhall необходимо добавить фотографию")
        super().save(*args, **kwargs)
        
        if self.image:
            try:
                img_path = self.image.path
                if img_path.lower().endswith('.heic'):
                    # Открываем HEIC файл
                    heif_file = pillow_heif.read_heif(img_path)
                    # Конвертируем в JPEG
                    image_pil = Image.frombytes(
                        heif_file.mode, 
                        heif_file.size, 
                        heif_file.data,
                        "raw",
                    )
                    # Создаем новое имя файла
                    new_path = img_path.replace('.heic', '.jpg')
                    # Сохраняем как JPEG
                    image_pil.save(new_path, 'JPEG')
                    # Обновляем путь к файлу
                    self.image.name = self.image.name.replace('.heic', '.jpg')
                    # Удаляем старый HEIC файл
                    os.remove(img_path)
                    # Сохраняем изменения
                    super().save(*args, **kwargs)
            except Exception as e:
                print(f"Ошибка при конвертации HEIC: {str(e)}")

    def __str__(self):
        return self.title

    def increment_views(self):
        """Увеличивает счетчик просмотров"""
        self.views += 1
        self.save(update_fields=['views'])

class Message(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages', null=True, blank=True)
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages', null=True, blank=True)
    content = models.TextField()
    image = models.ImageField(upload_to='message_images/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    is_system = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        if self.image:
            try:
                img_path = self.image.path
                if img_path.lower().endswith('.heic'):
                    # Открываем HEIC файл
                    heif_file = pillow_heif.read_heif(img_path)
                    # Конвертируем в JPEG
                    image_pil = Image.frombytes(
                        heif_file.mode, 
                        heif_file.size, 
                        heif_file.data,
                        "raw",
                    )
                    # Создаем новое имя файла
                    new_path = img_path.replace('.heic', '.jpg')
                    # Сохраняем как JPEG
                    image_pil.save(new_path, 'JPEG')
                    # Обновляем путь к файлу
                    self.image.name = self.image.name.replace('.heic', '.jpg')
                    # Удаляем старый HEIC файл
                    os.remove(img_path)
                    # Сохраняем изменения
                    super().save(*args, **kwargs)
            except Exception as e:
                print(f"Ошибка при конвертации HEIC: {str(e)}")

    def __str__(self):
        return f"Message about {self.item.title}"
