import os
import sys

import django

# Setup Django environment manually
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

def force_password_change_for_all_users():
    users_to_update = User.objects.exclude(is_superuser=True).exclude(user_type=User.Types.ADMIN)
    count = users_to_update.update(force_password_change=True)
    print(f"Updated {count} users to force password change on next login.")

if __name__ == '__main__':
    force_password_change_for_all_users()
