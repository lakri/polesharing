from django.contrib import admin
from .models import Item, Reservation

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'price', 'owner', 'is_reserved', 'created_at')
    list_filter = ('is_reserved', 'created_at')
    search_fields = ('title', 'description')

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('item', 'user', 'created_at', 'expires_at')
    list_filter = ('created_at', 'expires_at')
    search_fields = ('item__title', 'user__username')
