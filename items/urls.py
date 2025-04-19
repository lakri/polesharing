from django.urls import path
from . import views

urlpatterns = [
    path('', views.item_list, name='item_list'),
    path('create/', views.item_create, name='item_create'),
    path('reserve/<int:pk>/', views.item_reserve, name='item_reserve'),
    path('my-items/', views.my_items, name='my_items'),
    path('my-reservations/', views.my_reservations, name='my_reservations'),
    path('signup/', views.signup, name='signup'),
    path('cancel-reservation/<int:pk>/', views.cancel_reservation, name='cancel_reservation'),
    path('mark-sold/<int:pk>/', views.mark_as_sold, name='mark_sold'),
] 