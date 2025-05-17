from django.shortcuts import render
from django.shortcuts import render, redirect
from django.conf import settings
from home.supabase_client import supabase
import os
import uuid


def homepage_view(request):
    return render(request, 'home/index.html')


def signup_view(request):
    if request.method == "POST":
        full_name = request.POST.get("name")
        username = request.POST.get("username")
        password = request.POST.get("password")
        bio = request.POST.get("bio")
        profile_picture = request.FILES.get("profile_picture")

        # ❗ Validate that all fields are filled
        if not all([full_name, username, password, bio, profile_picture]):
            return render(request, "home/sign_up.html", {
                "error": "Please fill out all fields including the profile picture."
            })

        # ✅ 1. Supabase Auth signup
        try:
            auth_response = supabase.auth.sign_up({
                "email": username,
                "password": password
            })

            if not auth_response.user:
                return render(request, "home/sign_up.html", {
                    "error": "Failed to register user."
                })

            user_id = auth_response.user.id
        except Exception as e:
            return render(request, "home/sign_up.html", {
                "error": f"Sign up failed: {str(e)}"
            })


        profile_url = ""

        # ✅ 2. Upload image to Supabase Storage (safe)
        if profile_picture:
            try:
                file_ext = os.path.splitext(profile_picture.name)[-1]
                storage_path = f"profile_pictures/{uuid.uuid4()}{file_ext}"
                file_bytes = profile_picture.read()

                supabase.storage.from_("files").upload(
                    path=storage_path,
                    file=file_bytes,
                    file_options={"content-type": profile_picture.content_type}
                )

                profile_url = supabase.storage.from_("files").get_public_url(storage_path)

            except Exception as upload_error:
                print("Image upload failed:", upload_error)
                return render(request, "home/sign_up.html", {
                    "error": f"Image upload failed: {upload_error}"
                })

        # ✅ 3. Insert user into `accounts` table
        try:
            supabase.table("accounts").insert({
                "user_id": user_id,
                "full_name": full_name,
                "username": username,
                "bio": bio,
                "password": password,  # ⚠️ still plain text
                "profile_url": profile_url
            }).execute()
        except Exception as insert_error:
            print("Account insert failed:", insert_error)
            return render(request, "home/sign_up.html", {
                "error": f"Account creation failed: {insert_error}"
            })

        return redirect("home")

    return render(request, "home/sign_up.html")


def signin_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        try:
            response = (
                supabase
                .table("accounts")
                .select("*")
                .eq("username", username)
                .eq("password", password)  # ⚠️ Plain text comparison (not safe for production)
                .single()
                .execute()
            )

            if response.data:
                return render(request, "home/profile.html", {"user": response.data})

            else:
                return render(request, "home/index.html", {"error": "❌ Invalid credentials."})

        except Exception as e:
            print("Login error:", e)
            return render(request, "home/index.html", {"error": "⚠️ Something went wrong. Try again."})

    return render(request, "home/index.html")
