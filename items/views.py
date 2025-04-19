from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.forms import UserCreationForm
from .models import Item, Reservation
from .forms import ItemForm, ReservationForm

def item_list(request):
    items = Item.objects.filter(is_sold=False)
    return render(request, 'items/item_list.html', {'items': items})

@login_required
def item_create(request):
    if request.method == 'POST':
        form = ItemForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.owner = request.user
            item.save()
            messages.success(request, 'Товар успешно добавлен!')
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
def mark_as_sold(request, pk):
    item = get_object_or_404(Item, pk=pk, owner=request.user)
    
    # Если товар забронирован, удаляем бронирование
    if item.is_reserved:
        Reservation.objects.filter(item=item).delete()
        item.is_reserved = False
        item.save()
    
    # Отмечаем товар как проданный
    item.is_sold = True
    item.save()
    messages.success(request, 'Товар отмечен как проданный!')
    
    return redirect('my_items')

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Регистрация прошла успешно! Теперь вы можете войти.')
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})
