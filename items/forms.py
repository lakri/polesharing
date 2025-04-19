from django import forms
from .models import Item, Reservation
from PIL import Image
import pillow_heif

class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ['title', 'description', 'image', 'price']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            try:
                # Проверяем, является ли файл HEIC
                if image.name.lower().endswith('.heic'):
                    # Открываем HEIC файл
                    heif_file = pillow_heif.read_heif(image)
                    # Конвертируем в JPEG
                    image_pil = Image.frombytes(
                        heif_file.mode, 
                        heif_file.size, 
                        heif_file.data,
                        "raw",
                    )
                    # Сохраняем как JPEG
                    image_pil.save(image.name.replace('.heic', '.jpg'), 'JPEG')
                    # Обновляем имя файла
                    image.name = image.name.replace('.heic', '.jpg')
            except Exception as e:
                raise forms.ValidationError(f'Ошибка при обработке изображения: {str(e)}')
        return image

class ReservationForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = [] 