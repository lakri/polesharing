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

def item_list(request):
    items = Item.objects.filter(is_sold=False).order_by('-created_at')
    return render(request, 'items/item_list.html', {'items': items})

@login_required
def item_create(request):
    if request.method == 'POST':
        form = ItemForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.owner = request.user
            item.save()
            messages.success(request, 'Item added successfully!')
            return redirect('item_list')
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
    item = get_object_or_404(Item, pk=pk, owner=request.user)
    item.is_sold = True
    item.save()
    messages.success(request, 'Item marked as sold!')
    return redirect('my_items')

@login_required
def item_detail(request, pk):
    item = get_object_or_404(Item, pk=pk)
    
    # Определяем собеседника
    if request.user == item.owner:
        # Если текущий пользователь - владелец, ищем последнее сообщение от покупателя
        last_message = Message.objects.filter(
            Q(sender=request.user) | Q(receiver=request.user),
            item=item
        ).exclude(sender=request.user).order_by('-created_at').first()
        
        if last_message:
            conversation_with = last_message.sender
        else:
            conversation_with = None
    else:
        # Если текущий пользователь - покупатель, собеседник - владелец товара
        conversation_with = item.owner
    
    # Получаем сообщения только с выбранным собеседником
    if conversation_with:
        item_messages = Message.objects.filter(
            Q(sender=request.user, receiver=conversation_with) | 
            Q(sender=conversation_with, receiver=request.user),
            item=item
        ).order_by('created_at')
        
        # Помечаем все сообщения как прочитанные
        Message.objects.filter(
            item=item,
            receiver=request.user,
            is_read=False
        ).update(is_read=True)
    else:
        item_messages = Message.objects.none()
    
    if request.method == 'POST':
        form = MessageForm(request.POST, request.FILES)
        if form.is_valid():
            message = form.save(commit=False)
            message.item = item
            message.sender = request.user
            message.is_system = False
            
            if conversation_with:
                message.receiver = conversation_with
                message.save()
                messages.success(request, 'Message sent successfully!')
                return redirect('item_detail', pk=pk)
            else:
                messages.error(request, 'No conversation partner found.')
                return redirect('item_detail', pk=pk)
    else:
        form = MessageForm()
    
    # Проверяем, есть ли сообщения для отображения формы
    has_messages = item_messages.exists()
    
    return render(request, 'items/item_detail.html', {
        'item': item,
        'form': form,
        'messages': item_messages,
        'conversation_with': conversation_with,
        'has_messages': has_messages
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
        # Получаем последнее сообщение
        last_message = item.messages.filter(
            Q(sender=request.user) | Q(receiver=request.user)
        ).order_by('-created_at').first()
        
        # Определяем собеседника
        if request.user == item.owner:
            # Если текущий пользователь - владелец, ищем последнее сообщение от покупателя
            conversation_with = item.messages.exclude(sender=request.user).order_by('-created_at').first().sender
        else:
            # Если текущий пользователь - покупатель, собеседник - владелец товара
            conversation_with = item.owner
        
        # Проверяем, прочитано ли сообщение
        is_read = last_message.is_read if last_message else True
        
        items_with_conversations.append({
            'item': item,
            'conversation_with': conversation_with,
            'last_message': last_message,
            'is_read': is_read
        })
    
    return render(request, 'items/my_messages.html', {
        'items_with_conversations': items_with_conversations
    })

def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('item_list')
    else:
        form = SignUpForm()
    return render(request, 'registration/signup.html', {'form': form})

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
    item = get_object_or_404(Item, pk=pk, owner=request.user)
    if request.method == 'POST':
        item.is_in_airhall = not item.is_in_airhall
        if not item.is_in_airhall:
            item.airhall_image = None
            item.airhall_location = None
        item.save()
        messages.success(request, f'Item {"marked as in" if item.is_in_airhall else "removed from"} Airhall')
        return redirect('item_detail', pk=pk)
    return redirect('item_detail', pk=pk)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def user_list(request):
    users = User.objects.all().order_by('username')
    return render(request, 'items/user_list.html', {'users': users})
