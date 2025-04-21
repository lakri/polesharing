from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Item, Message
from PIL import Image
import pillow_heif
import os
from django.core.files.uploadedfile import InMemoryUploadedFile
import magic

class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user

class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ['title', 'description', 'image', 'price', 'category', 'is_in_airhall', 'airhall_image', 'airhall_location']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'is_in_airhall': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        is_in_airhall = cleaned_data.get('is_in_airhall')
        airhall_image = cleaned_data.get('airhall_image')

        if is_in_airhall and not airhall_image:
            self.add_error('airhall_image', 'Для товара в airhall необходимо добавить фотографию')

        return cleaned_data

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if not image:
            return image
            
        # Check file extension
        if not image.name.lower().endswith(('.jpg', '.jpeg', '.png', '.heic')):
            raise forms.ValidationError('Please upload a valid image file (JPG, JPEG, PNG, or HEIC).')
        
        # Check file size (max 5MB)
        if image.size > 5 * 1024 * 1024:
            raise forms.ValidationError('Image file too large (max 5MB).')
        
        try:
            # Determine MIME type
            mime = magic.Magic(mime=True)
            content_type = mime.from_buffer(image.read())
            image.seek(0)  # Reset file pointer
            
            # Check if file is an image
            if not content_type.startswith('image/'):
                raise forms.ValidationError('Please upload a valid image file.')
            
            # For HEIC files
            if image.name.lower().endswith('.heic') or content_type == 'image/heic':
                try:
                    # Create temporary file
                    temp_file = image.temporary_file_path()
                    
                    # Open HEIC file
                    heif_file = pillow_heif.read_heif(temp_file)
                    
                    # Convert to JPEG
                    image_pil = Image.frombytes(
                        heif_file.mode, 
                        heif_file.size, 
                        heif_file.data,
                        "raw",
                    )
                    
                    # Create new InMemoryUploadedFile
                    from io import BytesIO
                    output = BytesIO()
                    image_pil.save(output, format='JPEG')
                    output.seek(0)
                    
                    new_image = InMemoryUploadedFile(
                        output,
                        'ImageField',
                        image.name.replace('.heic', '.jpg'),
                        'image/jpeg',
                        output.getbuffer().nbytes,
                        None
                    )
                    
                    return new_image
                except Exception as e:
                    raise forms.ValidationError(f'Error processing HEIC image: {str(e)}')
            
            return image
        except Exception as e:
            raise forms.ValidationError(f'Error processing image: {str(e)}')

    def clean_airhall_image(self):
        image = self.cleaned_data.get('airhall_image')
        if image:
            # Проверяем расширение файла
            if not image.name.lower().endswith(('.jpg', '.jpeg', '.png', '.heic')):
                raise forms.ValidationError('Пожалуйста, загрузите изображение в формате JPG, JPEG, PNG или HEIC.')
            
            # Проверяем размер файла (максимум 5MB)
            if image.size > 5 * 1024 * 1024:
                raise forms.ValidationError('Размер файла не должен превышать 5MB.')
            
            # Для HEIC файлов
            if image.name.lower().endswith('.heic'):
                try:
                    # Определяем MIME тип
                    mime = magic.Magic(mime=True)
                    content_type = mime.from_buffer(image.read())
                    image.seek(0)  # Сбрасываем указатель файла
                    
                    # Проверяем, является ли файл изображением
                    if not content_type.startswith('image/'):
                        raise forms.ValidationError('Пожалуйста, загрузите валидное изображение.')
                    
                    # Создаем временный файл
                    temp_file = image.temporary_file_path()
                    
                    # Открываем HEIC файл
                    heif_file = pillow_heif.read_heif(temp_file)
                    
                    # Конвертируем в JPEG
                    image_pil = Image.frombytes(
                        heif_file.mode, 
                        heif_file.size, 
                        heif_file.data,
                        "raw",
                    )
                    
                    # Создаем новый InMemoryUploadedFile
                    from io import BytesIO
                    output = BytesIO()
                    image_pil.save(output, format='JPEG')
                    output.seek(0)
                    
                    new_image = InMemoryUploadedFile(
                        output,
                        'ImageField',
                        image.name.replace('.heic', '.jpg'),
                        'image/jpeg',
                        output.getbuffer().nbytes,
                        None
                    )
                    
                    return new_image
                except Exception as e:
                    raise forms.ValidationError(f'Ошибка при обработке HEIC изображения: {str(e)}')
        
        return image

class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['content', 'image']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Write your message here...'}),
        }

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if not image:
            return image
            
        # Check file extension
        if not image.name.lower().endswith(('.jpg', '.jpeg', '.png', '.heic')):
            raise forms.ValidationError('Please upload a valid image file (JPG, JPEG, PNG, or HEIC).')
        
        # Check file size (max 5MB)
        if image.size > 5 * 1024 * 1024:
            raise forms.ValidationError('Image file too large (max 5MB).')
        
        try:
            # Determine MIME type
            mime = magic.Magic(mime=True)
            content_type = mime.from_buffer(image.read())
            image.seek(0)  # Reset file pointer
            
            # Check if file is an image
            if not content_type.startswith('image/'):
                raise forms.ValidationError('Please upload a valid image file.')
            
            # For HEIC files
            if image.name.lower().endswith('.heic') or content_type == 'image/heic':
                try:
                    # Create temporary file
                    temp_file = image.temporary_file_path()
                    
                    # Open HEIC file
                    heif_file = pillow_heif.read_heif(temp_file)
                    
                    # Convert to JPEG
                    image_pil = Image.frombytes(
                        heif_file.mode, 
                        heif_file.size, 
                        heif_file.data,
                        "raw",
                    )
                    
                    # Create new InMemoryUploadedFile
                    from io import BytesIO
                    output = BytesIO()
                    image_pil.save(output, format='JPEG')
                    output.seek(0)
                    
                    new_image = InMemoryUploadedFile(
                        output,
                        'ImageField',
                        image.name.replace('.heic', '.jpg'),
                        'image/jpeg',
                        output.getbuffer().nbytes,
                        None
                    )
                    
                    return new_image
                except Exception as e:
                    raise forms.ValidationError(f'Error processing HEIC image: {str(e)}')
            
            return image
        except Exception as e:
            raise forms.ValidationError(f'Error processing image: {str(e)}') 