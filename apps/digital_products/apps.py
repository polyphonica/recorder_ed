from django.apps import AppConfig


class DigitalProductsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.digital_products'
    verbose_name = 'Digital Products'

    def ready(self):
        import apps.digital_products.signals  # noqa
