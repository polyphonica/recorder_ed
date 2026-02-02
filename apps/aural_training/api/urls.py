from django.urls import path
from .views import (
    LoadProgressAPIView, StartSessionAPIView,
    RecordAnswerAPIView, UnlockIntervalsAPIView, EndSessionAPIView
)

app_name = 'aural_training_api'

urlpatterns = [
    path('progress/', LoadProgressAPIView.as_view(), name='load-progress'),
    path('session/start/', StartSessionAPIView.as_view(), name='start-session'),
    path('session/answer/', RecordAnswerAPIView.as_view(), name='record-answer'),
    path('session/unlock/', UnlockIntervalsAPIView.as_view(), name='unlock-intervals'),
    path('session/end/', EndSessionAPIView.as_view(), name='end-session'),
]
