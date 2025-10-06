from django.contrib.messages import get_messages


def messages(request):
    """
    Ensure messages are available in all templates.
    """
    return {
        "django_messages": get_messages(request),
    }
