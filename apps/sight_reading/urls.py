from django.urls import path
from . import views

app_name = 'sight_reading'

urlpatterns = [
    # Teacher: Example library
    path('examples/', views.ExampleLibraryView.as_view(), name='example_library'),
    path('examples/create/', views.ExampleCreateView.as_view(), name='example_create'),
    path('examples/<uuid:pk>/', views.ExampleDetailView.as_view(), name='example_detail'),
    path('examples/<uuid:pk>/edit/', views.ExampleEditView.as_view(), name='example_edit'),
    path('examples/<uuid:pk>/delete/', views.ExampleDeleteView.as_view(), name='example_delete'),

    # Teacher: Set management
    path('sets/', views.SetLibraryView.as_view(), name='set_library'),
    path('sets/create/', views.SetCreateView.as_view(), name='set_create'),
    path('sets/<uuid:pk>/', views.SetDetailView.as_view(), name='set_detail'),
    path('sets/<uuid:pk>/edit/', views.SetEditView.as_view(), name='set_edit'),
    path('sets/<uuid:pk>/delete/', views.SetDeleteView.as_view(), name='set_delete'),
    path('sets/<uuid:pk>/add-example/', views.SetAddExampleView.as_view(), name='set_add_example'),
    path('sets/<uuid:pk>/remove/<uuid:item_pk>/', views.SetRemoveExampleView.as_view(), name='set_remove_example'),
    path('sets/<uuid:pk>/reorder/', views.SetReorderView.as_view(), name='set_reorder'),

    # Teacher: Assignments
    path('assignments/', views.AssignmentListView.as_view(), name='assignment_list'),
    path('assignments/create/', views.AssignmentCreateView.as_view(), name='assignment_create'),
    path('assignments/<uuid:pk>/', views.AssignmentDetailView.as_view(), name='assignment_detail'),
    path('assignments/<uuid:pk>/delete/', views.AssignmentDeleteView.as_view(), name='assignment_delete'),
    path('assignments/<uuid:pk>/toggle-lock/', views.AssignmentToggleLockView.as_view(), name='assignment_toggle_lock'),
    path('assignments/<uuid:pk>/complete/', views.AssignmentCompleteView.as_view(), name='assignment_complete'),
    path('assignments/<uuid:pk>/note-save/', views.AssignmentNoteSaveView.as_view(), name='assignment_note_save'),

    # Teacher + Student: Session
    path('assignments/<uuid:pk>/session/<int:position>/', views.SessionExerciseView.as_view(), name='session_exercise'),
    path('assignments/<uuid:pk>/session/<int:position>/grade/', views.SessionGradeView.as_view(), name='session_grade'),

    # Student
    path('my-assignments/', views.StudentAssignmentListView.as_view(), name='student_assignments'),
]
