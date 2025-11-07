from django.urls import path
from . import views

app_name = 'audioplayer'

urlpatterns = [
    # Teacher - Piece Library Management
    path('pieces/', views.piece_list, name='piece_list'),
    path('pieces/create/', views.piece_create, name='piece_create'),
    path('pieces/<int:pk>/', views.piece_detail, name='piece_detail'),
    path('pieces/<int:pk>/edit/', views.piece_edit, name='piece_edit'),
    path('pieces/<int:pk>/delete/', views.piece_delete, name='piece_delete'),

    # Student - Playback Interface
    path('lesson/<uuid:lesson_id>/player/', views.audio_player, name='audio_player'),
    path('lesson/<uuid:lesson_id>/pieces-json/', views.pieces_json, name='pieces_json'),
]
