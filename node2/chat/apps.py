from django.apps import AppConfig


class ChatConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "chat"

    def ready(self):
        """
        Import signals when app is ready, but don't execute database queries
        """
        # Import signals module but don't initialize database-dependent code
        try:
            import chat.signals
        except Exception as e:
            # Log but don't crash the app
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to import chat signals: {e}")
