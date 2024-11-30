from django.core.exceptions import ImproperlyConfigured
from django.conf import settings


def validate_environment():
    """
    Validate that all required environment variables are set.
    Called during Django startup to ensure configuration is complete.
    """
    required_settings = {
        "ANTHROPIC_API_KEY": "Anthropic API key is required for interaction analysis",
        "DJANGO_SECRET_KEY": "Django secret key is required for security",
    }

    # Only check Google settings if Google integration is enabled
    if "allauth.socialaccount.providers.google" in settings.INSTALLED_APPS:
        required_settings.update(
            {
                "GOOGLE_CLIENT_ID": "Google Client ID is required for Google integration",
                "GOOGLE_CLIENT_SECRET": "Google Client Secret is required for Google integration",
            }
        )

    missing_settings = []

    for setting, message in required_settings.items():
        if not getattr(settings, setting, None):
            missing_settings.append(f"{setting}: {message}")

    if missing_settings:
        raise ImproperlyConfigured(
            "Missing required environment variables:\n"
            + "\n".join(missing_settings)
            + "\nPlease check your .env file and environment variables."
        )
