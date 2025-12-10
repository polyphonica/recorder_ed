from django.urls import path
from . import views

app_name = 'audioplayer'

urlpatterns = [
    # Play-Along Library (Student & Teacher)
    path('library/', views.PlayAlongLibraryView.as_view(), name='library'),

    # Teacher - Piece Library Management
    path('pieces/', views.piece_list, name='piece_list'),
    path('pieces/create/', views.piece_create, name='piece_create'),
    path('pieces/<int:pk>/', views.piece_detail, name='piece_detail'),
    path('pieces/<int:pk>/edit/', views.piece_edit, name='piece_edit'),
    path('pieces/<int:pk>/delete/', views.piece_delete, name='piece_delete'),

    # Teacher - Composer Management
    path('composers/', views.composer_list, name='composer_list'),
    path('composers/create/', views.composer_create, name='composer_create'),
    path('composers/<int:pk>/edit/', views.composer_edit, name='composer_edit'),
    path('composers/<int:pk>/delete/', views.composer_delete, name='composer_delete'),

    # Student - Playback Interface (Course Lessons)
    path('lesson/<uuid:lesson_id>/player/', views.audio_player, name='audio_player'),
    path('lesson/<uuid:lesson_id>/pieces-json/', views.pieces_json, name='pieces_json'),

    # Student - Playback Interface (Private Teaching Lessons)
    path('private-lesson/<uuid:lesson_id>/player/', views.private_lesson_player, name='private_lesson_player'),
    path('private-lesson/<uuid:lesson_id>/pieces-json/', views.private_lesson_pieces_json, name='private_lesson_pieces_json'),

    # Student - Playback Interface (Library Pieces)
    path('library/piece/<int:piece_id>/player/', views.library_piece_player, name='library_piece_player'),
    path('library/piece/<int:piece_id>/pieces-json/', views.library_piece_json, name='library_piece_json'),
]
