# migrate_passwords.py
from django.conf import settings
import os
import django

# Required to load Django context if running outside manage.py
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "social_media.settings")
django.setup()

from home.supabase_client import supabase
from django.contrib.auth.hashers import make_password, is_password_usable

def migrate_plain_passwords():
    response = supabase.table("accounts").select("user_id, password").execute()
    users = response.data
    updated_count = 0

    for user in users:
        uid = user["user_id"]
        pw = user["password"]

        if is_password_usable(pw) and pw.startswith("pbkdf2_"):
            continue  # already hashed

        hashed = make_password(pw)
        supabase.table("accounts").update({"password": hashed}).eq("user_id", uid).execute()
        print(f"✅ Migrated user: {uid}")
        updated_count += 1

    print(f"\n🎉 Done. {updated_count} password(s) hashed.")

if __name__ == "__main__":
    migrate_plain_passwords()
