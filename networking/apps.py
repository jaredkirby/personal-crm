from django.apps import AppConfig


class NetworkingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "networking"

    def ready(self):
        """
        Validate environment variables when Django starts
        """
        from .env_validation import validate_environment

        validate_environment()
