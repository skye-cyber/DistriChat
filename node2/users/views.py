from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.csrf import csrf_protect
from .forms import CustomUserCreationForm, CustomAuthenticationForm
from .models import UserActivity


@csrf_protect
def register_view(request):
    """User registration view."""
    if request.user.is_authenticated:
        return redirect("chat:dashboard")

    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()

            # Log user activity
            UserActivity.objects.create(
                user=user,
                activity_type="login",
                description="User registered and logged in",
                ip_address=get_client_ip(request),
            )

            login(request, user)
            messages.success(request, "Registration successful! Welcome to DistriChat.")
            return redirect("chat:dashboard")
    else:
        form = CustomUserCreationForm()

    return render(request, "register.html", {"form": form})


@csrf_protect
def login_view(request):
    """User login view."""
    if request.user.is_authenticated:
        return redirect("chat:dashboard")

    if request.method == "POST":
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)

                # Update user online status
                user.is_online = True
                user.save()

                # Log user activity
                UserActivity.objects.create(
                    user=user,
                    activity_type="login",
                    description="User logged in",
                    ip_address=get_client_ip(request),
                )

                # Update lats seen
                request.user.update_last_seen()

                messages.success(request, f"Welcome back, {user.username}!")
                return redirect("chat:dashboard")
    else:
        form = CustomAuthenticationForm()

    return render(request, "login.html", {"form": form})


@login_required
def logout_view(request):
    """User logout view."""
    # Update user online status
    request.user.is_online = False

    # Update lats seen
    request.user.update_last_seen()

    # Log user activity
    UserActivity.objects.create(
        user=request.user,
        activity_type="logout",
        description="User logged out",
        ip_address=get_client_ip(request),
    )

    logout(request)
    messages.info(request, "You have been logged out successfully.")
    return redirect("index")


@login_required
def profile_view(request):
    """User profile view."""
    user = request.user
    user_activities = user.activities.all()[:10]  # Last 10 activities

    context = {
        "user": user,
        "activities": user_activities,
    }
    return render(request, "users/profile.html", context)


@login_required
def update_profile_view(request):
    """Update user profile."""
    if request.method == "POST":
        user = request.user
        user.email = request.POST.get("email", user.email)
        user.bio = request.POST.get("bio", user.bio)
        user.color_scheme = request.POST.get("color_scheme", user.color_scheme)
        user.notification_enabled = "notification_enabled" in request.POST
        user.sound_enabled = "sound_enabled" in request.POST

        if "avatar" in request.FILES:
            user.avatar = request.FILES["avatar"]

        user.save()
        messages.success(request, "Profile updated successfully!")
        return redirect("profile")

    return render(request, "users/update_profile.html")


def get_client_ip(request):
    """Get client IP address."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip
