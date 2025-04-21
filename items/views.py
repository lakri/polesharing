from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q, F
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Item, Message
from .forms import ItemForm, MessageForm, SignUpForm
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
    track_category_stats
)

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
def item_reserve(request, pk):
    item = get_object_or_404(Item, pk=pk)
    
    if item.is_reserved:
        messages.error(request, 'Этот товар уже забронирован!')
        return redirect('item_list')
    
    if request.method == 'POST':
        reservation = Reservation(item=item, user=request.user)
        reservation.save()
        item.is_reserved = True
        item.save()
        messages.success(request, 'Товар успешно забронирован на 24 часа!')
        return redirect('item_list')
    
    return render(request, 'items/reserve_confirm.html', {'item': item})

@login_required
def my_items(request):
    items = Item.objects.filter(owner=request.user).order_by('-created_at')
    return render(request, 'items/my_items.html', {'items': items})

@login_required
def my_reservations(request):
    reservations = Reservation.objects.filter(user=request.user)
    return render(request, 'items/my_reservations.html', {'reservations': reservations})

@login_required
def cancel_reservation(request, pk):
    reservation = get_object_or_404(Reservation, pk=pk, user=request.user)
    item = reservation.item
    
    if not reservation.is_expired():
        item.is_reserved = False
        item.save()
        reservation.delete()
        messages.success(request, 'Бронирование успешно отменено!')
    else:
        messages.error(request, 'Бронирование уже истекло!')
    
    return redirect('my_reservations')

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
    
    # Получаем сообщения только для текущего пользователя
    if request.user.is_authenticated:
        # Определяем собеседника
        if request.user == item.owner:
            # Если текущий пользователь - владелец, показываем сообщения только с последним покупателем
            last_buyer_message = Message.objects.filter(item=item).exclude(sender=request.user).order_by('-created_at').first()
            if last_buyer_message:
                message_list = Message.objects.filter(
                    Q(sender=request.user, receiver=last_buyer_message.sender) |
                    Q(sender=last_buyer_message.sender, receiver=request.user),
                    item=item
                ).order_by('created_at')
            else:
                message_list = None
        else:
            # Если текущий пользователь - покупатель, показываем сообщения только с владельцем
            message_list = Message.objects.filter(
                Q(sender=request.user, receiver=item.owner) |
                Q(sender=item.owner, receiver=request.user),
                item=item
            ).order_by('created_at')
    else:
        message_list = None
    
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
        'form': form
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
        # Определяем собеседника
        if request.user == item.owner:
            # Если текущий пользователь - владелец, ищем последнее сообщение от покупателя
            last_buyer_message = item.messages.exclude(sender=request.user).order_by('-created_at').first()
            if last_buyer_message:
                conversation_with = last_buyer_message.sender
                # Получаем сообщения только с этим покупателем
                messages = item.messages.filter(
                    Q(sender=request.user, receiver=conversation_with) |
                    Q(sender=conversation_with, receiver=request.user)
                )
                last_message = messages.order_by('-created_at').first()
                has_unread = messages.filter(receiver=request.user, is_read=False).exists()
                
                items_with_conversations.append({
                    'item': item,
                    'conversation_with': conversation_with,
                    'last_message': last_message,
                    'has_unread': has_unread
                })
        else:
            # Если текущий пользователь - покупатель, показываем только сообщения с владельцем
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
        'items_with_conversations': items_with_conversations
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
    return render(request, 'items/user_list.html', {'users': users})

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
