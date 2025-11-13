from django.urls import path
from . import views

app_name = 'messaging'

urlpatterns = [
    path('', views.inbox, name='inbox'),
    path('conversation/<uuid:conversation_id>/', views.conversation_detail, name='conversation_detail'),
    path('start/workshop/<uuid:workshop_id>/', views.start_workshop_conversation, name='start_workshop_conversation'),
]
