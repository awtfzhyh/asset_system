import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'asset_system.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()
username = 'admin'  # You can change your admin username here
email = 'awatifzahiyah0509@gmail.com'
password = 'Admin123!'  # Change this to your desired password

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print("--- SUPERUSER CREATED SUCCESSFULLY VIA SCRIPT ---")
else:
    print("--- SUPERUSER ALREADY EXISTS ---")