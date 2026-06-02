import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.contrib.auth import get_user_model

username = os.environ.get("DASHBOARD_ADMIN_USERNAME", "admin").strip() or "admin"
password = os.environ.get("DASHBOARD_ADMIN_PASSWORD", "1234")
email = os.environ.get("DASHBOARD_ADMIN_EMAIL", "admin@example.com").strip()

User = get_user_model()
user, _ = User.objects.get_or_create(
    username=username,
    defaults={"email": email, "is_staff": True, "is_superuser": True},
)
user.email = email
user.is_staff = True
user.is_superuser = True
user.set_password(password)
user.save()

print(f"bootstrap-admin: ready user={username}")
