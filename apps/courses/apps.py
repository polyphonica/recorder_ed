from django.apps import AppConfig


class CoursesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.courses'

    def ready(self):
        """Import signal handlers when the app is ready"""
        import apps.courses.signals  # noqa
