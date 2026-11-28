from django.apps import AppConfig


class TeacherTasksConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.teacher_tasks'
    label = 'teacher_tasks'
    verbose_name = 'Teacher tasks'

    def ready(self):
        from . import signals  # noqa: F401
