from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q, F
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Item, Message, UserProfile
from .forms import ItemForm, MessageForm, SignUpForm, UserStatusForm
from django.contrib.auth import login
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .analytics import (
    track_user_registration,
    track_item_creation,
    track_item_sold,
    track_first_message,
    track_airhall_status,
    track_item_view,
    track_message_sent,
    track_category_stats,
    track_user_status_change
)
from django.http import JsonResponse

def item_list(request):
    items = Item.objects.filter(is_sold=False).order_by('-created_at')
    
    # Отправляем статистику по категориям
    track_category_stats()
    
    return render(request, 'items/item_list.html', {'items': items})

@login_required
def item_create(request):
    if request.method == 'POST':
        form = ItemForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.owner = request.user
            item.is_banned = False
            item.save()
            # Отслеживаем создание товара
            track_item_creation(item)
            return redirect('item_detail', pk=item.pk)
    else:
        form = ItemForm()
    return render(request, 'items/item_form.html', {'form': form})

@login_required
def my_items(request):
    items = Item.objects.filter(owner=request.user).order_by('-created_at')
    return render(request, 'items/my_items.html', {'items': items})

@login_required
def mark_sold(request, pk):
    item = get_object_or_404(Item, pk=pk)
    if request.user == item.owner:
        item.is_sold = True
        item.save()
        # Отслеживаем продажу товара
        track_item_sold(item)
        messages.success(request, 'Item marked as sold!')
    return redirect('item_detail', pk=pk)

@login_required
def item_detail(request, pk):
    item = get_object_or_404(Item, pk=pk)
    
    # Увеличиваем счетчик просмотров и отправляем событие
    item.increment_views()
    track_item_view(item, request.user)
    
    # Инициализируем переменные по умолчанию
    message_list = None
    conversations = None
    
    # Получаем сообщения только для текущего пользователя
    if request.user.is_authenticated:
        if request.user == item.owner:
            # Для продавца - получаем список всех покупателей, с которыми есть переписка
            buyers = User.objects.filter(
                Q(sent_messages__item=item) | Q(received_messages__item=item)
            ).exclude(id=request.user.id).distinct()
            
            conversations = []
            for buyer in buyers:
                buyer_messages = Message.objects.filter(
                    Q(sender=request.user, receiver=buyer) |
                    Q(sender=buyer, receiver=request.user),
                    item=item
                ).order_by('created_at')
                
                last_message = buyer_messages.last()
                has_unread = buyer_messages.filter(receiver=request.user, is_read=False).exists()
                
                conversations.append({
                    'buyer': buyer,
                    'messages': buyer_messages,
                    'last_message': last_message,
                    'has_unread': has_unread
                })
        else:
            # Для покупателя - показываем сообщения только с владельцем
            message_list = Message.objects.filter(
                Q(sender=request.user, receiver=item.owner) |
                Q(sender=item.owner, receiver=request.user),
                item=item
            ).order_by('created_at')
    
    if request.method == 'POST':
        form = MessageForm(request.POST, request.FILES)
        if form.is_valid():
            message = form.save(commit=False)
            message.item = item
            message.sender = request.user
            
            # Определяем получателя сообщения
            if request.user == item.owner:
                # Если отправитель - владелец, получатель - выбранный покупатель
                buyer_id = request.POST.get('buyer_id')
                if buyer_id:
                    message.receiver = get_object_or_404(User, id=buyer_id)
                else:
                    messages.error(request, 'Please select a buyer to send message to')
                    return redirect('item_detail', pk=pk)
            else:
                # Если отправитель - покупатель, получатель - владелец
                message.receiver = item.owner
            
            message.save()
            
            # Отслеживаем отправку сообщения
            track_message_sent(message)
            
            # Проверяем, первое ли это сообщение по товару
            message_count = Message.objects.filter(item=item).count()
            if message_count == 1:
                track_first_message(item, message)
            
            messages.success(request, 'Message sent successfully!')
            return redirect('item_detail', pk=pk)
    else:
        form = MessageForm()
    
    return render(request, 'items/item_detail.html', {
        'item': item,
        'messages': message_list,
        'conversations': conversations,
        'form': form,
        'is_seller': request.user == item.owner
    })

@login_required
def my_messages(request):
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Получаем все товары, у которых есть сообщения с участием текущего пользователя
    items = Item.objects.filter(
        messages__sender=request.user
    ).distinct() | Item.objects.filter(
        messages__receiver=request.user
    ).distinct()
    
    items_with_conversations = []
    for item in items:
        if request.user == item.owner:
            # Для продавца - пропускаем, так как он будет видеть все чаты в карточке товара
            continue
        else:
            # Для покупателя - показываем только сообщения с владельцем
            messages = item.messages.filter(
                Q(sender=request.user, receiver=item.owner) |
                Q(sender=item.owner, receiver=request.user)
            )
            last_message = messages.order_by('-created_at').first()
            has_unread = messages.filter(receiver=request.user, is_read=False).exists()
            
            items_with_conversations.append({
                'item': item,
                'conversation_with': item.owner,
                'last_message': last_message,
                'has_unread': has_unread
            })
    
    return render(request, 'items/my_messages.html', {
        'items_with_conversations': items_with_conversations,
        'is_seller': False  # В шаблоне будем использовать это для отображения соответствующего интерфейса
    })

def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Отслеживаем регистрацию пользователя
            track_user_registration(user)
            login(request, user)
            return redirect('item_list')
    else:
        form = SignUpForm()
    return render(request, 'items/signup.html', {'form': form})

@login_required
def item_edit(request, pk):
    item = get_object_or_404(Item, pk=pk, owner=request.user)
    if request.method == 'POST':
        form = ItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, 'Item updated successfully!')
            return redirect('item_detail', pk=pk)
    else:
        form = ItemForm(instance=item)
    return render(request, 'items/item_form.html', {'form': form})

@login_required
def toggle_airhall(request, pk):
    item = get_object_or_404(Item, pk=pk)
    if request.user != item.owner:
        messages.error(request, 'You do not have permission to modify this item.')
        return redirect('item_detail', pk=pk)
    
    if request.method == 'POST':
        if not item.is_in_airhall:
            # Получаем данные из формы
            airhall_image = request.FILES.get('airhall_image')
            airhall_location = request.POST.get('airhall_location')
            
            if not airhall_image or not airhall_location:
                messages.error(request, 'Please provide both an image and location for the item in airhall.')
                return redirect('item_detail', pk=pk)
            
            # Обновляем данные товара
            item.airhall_image = airhall_image
            item.airhall_location = airhall_location
            item.is_in_airhall = True
            item.save()
            
            # Отслеживаем изменение статуса airhall
            track_airhall_status(item, True)
            messages.success(request, 'Item has been marked as in airhall.')
        else:
            item.is_in_airhall = False
            item.save()
            
            # Отслеживаем изменение статуса airhall
            track_airhall_status(item, False)
            messages.success(request, 'Item has been removed from airhall.')
    
    return redirect('item_detail', pk=pk)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def user_list(request):
    users = User.objects.all().order_by('username')
    
    # Create UserProfile for users who don't have one
    for user in users:
        UserProfile.objects.get_or_create(user=user)
    
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        if user_id:
            user = get_object_or_404(User, id=user_id)
            form = UserStatusForm(request.POST, instance=user.profile)
            if form.is_valid():
                form.save()
                messages.success(request, f'Status updated for {user.username}')
                return redirect('user_list')
    
    return render(request, 'items/user_list.html', {
        'users': users,
        'status_form': UserStatusForm()
    })

def send_message(request, pk):
    item = get_object_or_404(Item, pk=pk)
    if request.method == 'POST':
        form = MessageForm(request.POST, request.FILES)
        if form.is_valid():
            message = form.save(commit=False)
            message.item = item
            message.sender = request.user
            
            # Определяем получателя сообщения
            if request.user == item.owner:
                # Если отправитель - владелец, получатель - последний отправитель
                last_message = Message.objects.filter(item=item).exclude(sender=request.user).last()
                if last_message:
                    message.receiver = last_message.sender
            else:
                # Если отправитель - покупатель, получатель - владелец
                message.receiver = item.owner
            
            message.save()
            
            # Проверяем, первое ли это сообщение по товару
            message_count = Message.objects.filter(item=item).count()
            if message_count == 1:
                track_first_message(item, message)
            
            messages.success(request, 'Message sent successfully!')
            return redirect('item_detail', pk=pk)
    else:
        form = MessageForm()
    return render(request, 'items/send_message.html', {'form': form, 'item': item})

def mark_in_airhall(request, pk):
    item = get_object_or_404(Item, pk=pk)
    if request.user == item.seller:
        item.is_in_airhall = True
        item.save()
        # Отслеживаем изменение статуса airhall
        track_airhall_status(item, True)
        messages.success(request, 'Item marked as in airhall!')
    return redirect('item_detail', pk=pk)

def remove_from_airhall(request, pk):
    item = get_object_or_404(Item, pk=pk)
    if request.user == item.seller:
        item.is_in_airhall = False
        item.save()
        # Отслеживаем изменение статуса airhall
        track_airhall_status(item, False)
        messages.success(request, 'Item removed from airhall!')
    return redirect('item_detail', pk=pk)

@login_required
def create_item(request):
    if request.method == 'POST':
        form = ItemForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.owner = request.user
            item.save()
            track_item_creation(item)  # Track item creation
            messages.success(request, 'Item created successfully!')
            return redirect('item_detail', item_id=item.id)
    else:
        form = ItemForm()
    return render(request, 'items/create_item.html', {'form': form})

@login_required
def mark_as_sold(request, item_id):
    item = get_object_or_404(Item, id=item_id)
    if request.user == item.owner:
        item.is_sold = True
        item.save()
        track_item_sold(item)  # Track item sold
        messages.success(request, 'Item marked as sold!')
    return redirect('item_detail', item_id=item.id)

@login_required
def update_airhall_status(request, item_id):
    item = get_object_or_404(Item, id=item_id)
    if request.user == item.owner:
        is_in_airhall = request.POST.get('is_in_airhall') == 'true'
        item.is_in_airhall = is_in_airhall
        item.save()
        track_airhall_status(item, is_in_airhall)  # Track airhall status change
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=403)

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Create user profile
            UserProfile.objects.create(user=user)
            # Track user registration
            track_user_registration(user)
            login(request, user)
            messages.success(request, 'Registration successful!')
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})
