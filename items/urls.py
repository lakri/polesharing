from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.item_list, name='item_list'),
    path('item/create/', views.item_create, name='item_create'),
    path('item/<int:pk>/', views.item_detail, name='item_detail'),
    path('item/<int:pk>/edit/', views.item_edit, name='item_edit'),
    path('item/<int:pk>/sold/', views.mark_sold, name='mark_sold'),
    path('item/<int:pk>/toggle_airhall/', views.toggle_airhall, name='toggle_airhall'),
    path('my-items/', views.my_items, name='my_items'),
    path('my-messages/', views.my_messages, name='my_messages'),
    path('signup/', views.signup, name='signup'),
    path('users/', views.user_list, name='user_list'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) 