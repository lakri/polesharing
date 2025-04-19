from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.contrib.auth.forms import UserCreationForm
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
    if request.method == 'POST':
        form = MessageForm(request.POST, request.FILES)
        if form.is_valid():
            message = form.save(commit=False)
            message.item = item
            message.sender = request.user
            # Если отправитель - владелец товара, получатель - последний отправитель сообщения
            if request.user == item.owner:
                last_message = Message.objects.filter(item=item).exclude(sender=request.user).order_by('-created_at').first()
                if last_message:
                    message.receiver = last_message.sender
                else:
                    messages.error(request, 'No messages to reply to.')
                    return redirect('item_detail', pk=pk)
            else:
                message.receiver = item.owner
            message.save()
            messages.success(request, 'Message sent successfully!')
            return redirect('item_detail', pk=pk)
    else:
        form = MessageForm()
    
    # Получаем все сообщения, связанные с этим товаром
    item_messages = Message.objects.filter(item=item).order_by('created_at')
    
    return render(request, 'items/item_detail.html', {
        'item': item,
        'form': form,
        'messages': item_messages
    })

@login_required
def my_messages(request):
    # Получаем все сообщения, где пользователь является отправителем или получателем
    user_messages = Message.objects.filter(
        Q(sender=request.user) | Q(receiver=request.user)
    ).order_by('-created_at')
    
    return render(request, 'items/my_messages.html', {'messages': user_messages})

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
