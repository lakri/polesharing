from django.urls import path
from . import views

urlpatterns = [
    path('', views.item_list, name='item_list'),
    path('item/new/', views.item_create, name='item_create'),
    path('item/<int:pk>/', views.item_detail, name='item_detail'),
    path('item/<int:pk>/edit/', views.item_edit, name='item_edit'),
    path('item/<int:pk>/toggle-airhall/', views.toggle_airhall, name='toggle_airhall'),
    path('my-items/', views.my_items, name='my_items'),
    path('item/<int:pk>/mark-sold/', views.mark_sold, name='mark_sold'),
    path('my-messages/', views.my_messages, name='my_messages'),
] 