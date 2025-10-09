from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

UserModel = get_user_model()


class EmailBackend(ModelBackend):
    """
    Custom authentication backend that allows login using email or username.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        # Normalize the username field (could be an email)
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)

        try:
            # Try to get the user by email or username
            user = (
                UserModel.objects.get(email__iexact=username)
                if "@" in username
                else UserModel.objects.get(username__iexact=username)
            )
        except UserModel.DoesNotExist:
            return None

        # Check password
        if user.check_password(password):
            return user
        return None
