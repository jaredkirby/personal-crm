from django.apps import AppConfig


class NetworkingBaseConfig(AppConfig):
    name = "networking_base"

    def ready(self):
        """Import signals when Django starts"""
        import networking_base.signals  # noqa
