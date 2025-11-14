from django.urls import path
from . import views

app_name = 'messaging'

urlpatterns = [
    path('', views.inbox, name='inbox'),
    path('conversation/<uuid:conversation_id>/', views.conversation_detail, name='conversation_detail'),
    path('start/workshop/<uuid:workshop_id>/', views.start_workshop_conversation, name='start_workshop_conversation'),
    path('start/course/<slug:course_slug>/', views.start_course_conversation, name='start_course_conversation'),
    path('start/private-teaching/<int:teacher_id>/', views.start_private_teaching_conversation, name='start_private_teaching_conversation'),
    path('start/private-teaching/<int:teacher_id>/<uuid:child_profile_id>/', views.start_private_teaching_conversation, name='start_private_teaching_conversation_child'),
]
