from django.dispatch import receiver
from django.db.models.signals import post_save
from django.contrib.auth import get_user_model
from users.models import UserProfile


@receiver(post_save, sender=get_user_model())
def create_user_profile(sender, instance, created, **kwargs):
    """Automatically create user profile when a new user is created"""
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=get_user_model())
def save_user_profile(sender, instance, **kwargs):
    """Automatically save user profile when user is saved"""
    if hasattr(instance, "profile"):
        instance.profile.save()
