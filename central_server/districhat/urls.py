from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from users import views as user_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", TemplateView.as_view(template_name="index.html"), name="index"),
    path("users/", include("users.urls")),
    path("chat/", include("chat.urls")),
    path("nodes/", include("nodes.urls")),
    # Redirect for old auth URLs
    path("accounts/login/", user_views.login_view, name="login_redirect"),
    path("accounts/logout/", user_views.logout_view, name="logout_redirect"),
    path("__reload__/", include("django_browser_reload.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
