from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from PIL import Image
import pillow_heif
import os

class Item(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    image = models.ImageField(upload_to='items/')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    is_reserved = models.BooleanField(default=False)
    is_sold = models.BooleanField(default=False)

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
        return self.title

class Reservation(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(hours=24)
        super().save(*args, **kwargs)

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"{self.user.username} - {self.item.title}"
