from django.urls import path

from . import clip_views, views

app_name = 'practice'

urlpatterns = [
    path('practice/log/', views.LogPracticeView.as_view(), name='log_practice'),
    path('practice/', views.PracticeLogView.as_view(), name='practice_log'),
    path('practice/print/', views.PracticeLogPrintView.as_view(), name='practice_log_print'),
    path('practice/<uuid:pk>/edit/', views.EditPracticeView.as_view(), name='edit_practice'),
    path('practice/<uuid:pk>/delete/', views.DeletePracticeView.as_view(), name='delete_practice'),
    path('teacher/students/<int:student_id>/practice/', views.TeacherStudentPracticeView.as_view(), name='teacher_student_practice'),
    path('teacher/practice/<uuid:entry_id>/comment/', views.AddPracticeCommentView.as_view(), name='add_practice_comment'),

    # Practice clips: student side
    path('practice/clips/upload/', clip_views.UploadPendingClipView.as_view(), name='upload_pending_clip'),
    path('practice/<uuid:entry_id>/clips/add/', clip_views.AddClipView.as_view(), name='add_clip'),
    path('practice/clips/<uuid:pk>/status/', clip_views.ClipStatusView.as_view(), name='clip_status'),
    path('practice/clips/<uuid:pk>/delete/', clip_views.DeleteClipView.as_view(), name='delete_clip'),
    path('practice/clips/<uuid:pk>/keep/', clip_views.ToggleKeepClipView.as_view(), name='toggle_keep_clip'),
    path('practice/clips/<uuid:pk>/follow-up/', clip_views.AddStudentFollowUpView.as_view(), name='clip_follow_up'),
    path('practice/clips/<uuid:pk>/audio/', clip_views.ClipAudioView.as_view(), name='clip_audio'),
    path('practice/clip-replies/<uuid:pk>/audio/', clip_views.ClipReplyAudioView.as_view(), name='clip_reply_audio'),

    # Practice clips: teacher side
    path('teacher/clips/', clip_views.TeacherClipInboxView.as_view(), name='teacher_clip_inbox'),
    path('teacher/clips/<uuid:pk>/', clip_views.TeacherClipDetailView.as_view(), name='teacher_clip_detail'),
    path('teacher/clips/<uuid:pk>/reply/', clip_views.AddClipReplyView.as_view(), name='add_clip_reply'),
    path('teacher/clips/<uuid:pk>/done/', clip_views.MarkClipDoneView.as_view(), name='mark_clip_done'),
]
