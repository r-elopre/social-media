from django.shortcuts import render
from django.shortcuts import render, redirect
from django.conf import settings
from home.supabase_client import supabase
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseRedirect
from django.utils import timezone
from pytz import timezone
import datetime
import os
import uuid


def homepage_view(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("signin")

    try:
        user_info = (
            supabase
            .table("accounts")
            .select("*")
            .eq("user_id", user_id)
            .single()
            .execute()
        )

        messages_response = (
            supabase
            .table("chats")
            .select("*")
            .or_(
                f"receiver_id.eq.{user_id},sender_id.eq.{user_id}"
            )
            .order("created_at", desc=True)
            .execute()
        )

        seen_users = set()
        messages = []
        manila = timezone("Asia/Manila")

        for msg in messages_response.data:
            is_sender = msg["sender_id"] == user_id
            other_user_id = msg["receiver_id"] if is_sender else msg["sender_id"]

            if other_user_id in seen_users:
                continue
            seen_users.add(other_user_id)

            other_user_info = (
                supabase
                .table("accounts")
                .select("full_name, profile_url")
                .eq("user_id", other_user_id)
                .single()
                .execute()
            )

            local_time = datetime.datetime.fromisoformat(
                msg["created_at"].replace("Z", "+00:00")
            ).astimezone(manila).strftime("%b %d, %Y %I:%M %p")

            messages.append({
                "sender_id": other_user_id,
                "sender_name": other_user_info.data["full_name"],
                "sender_avatar": other_user_info.data["profile_url"],
                "content": msg["message"],
                "time": local_time,
                "is_you": is_sender,
            })

        return render(request, "home/profile.html", {
            "user": user_info.data,
            "messages": messages
        })

    except Exception as e:
        print("Error loading profile:", e)
        return redirect("signin")


def logout_view(request):
    request.session.flush()  # Clear all session data
    return redirect("signin")  # Redirect to login page


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
                .eq("password", password)  # ⚠️ Plain text comparison
                .single()
                .execute()
            )

            if response.data:
                request.session["user_id"] = response.data["user_id"]
                return redirect("home")  # ✅ Redirect to avoid form resubmission
            else:
                return render(request, "home/index.html", {"error": "❌ Invalid credentials."})

        except Exception as e:
            print("Login error:", e)
            return render(request, "home/index.html", {"error": "⚠️ Something went wrong. Try again."})

    return render(request, "home/index.html")


@csrf_exempt
def search_users_view(request):
    query = request.GET.get("q", "").replace(" ", "").lower()

    try:
        response = supabase.table("accounts").select("full_name,username,profile_url").execute()
        if not response.data:
            return JsonResponse([], safe=False)

        matched_users = [
            user for user in response.data
            if query in user['full_name'].replace(" ", "").lower()
        ]
        return JsonResponse(matched_users, safe=False)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    


@csrf_exempt
def searched_profile_view(request, username):
    try:
        # Fetch receiver data
        response = (
            supabase
            .table("accounts")
            .select("*")
            .eq("username", username)
            .single()
            .execute()
        )
        if not response.data:
            return render(request, "home/searched_profile.html", {"error": "User not found"})

        receiver_data = response.data

        # If POST, insert new message
        if request.method == "POST":
            sender_id = request.session.get("user_id")
            receiver_id = receiver_data["user_id"]
            message = request.POST.get("message", "").strip()

            if sender_id and message:
                try:
                    supabase.table("chats").insert({
                        "sender_id": sender_id,
                        "receiver_id": receiver_id,
                        "message": message
                    }).execute()
                except Exception as insert_error:
                    print("Message insert failed:", insert_error)

        return render(request, "home/searched_profile.html", {
            "user": receiver_data
        })

    except Exception as e:
        return render(request, "home/searched_profile.html", {
            "error": f"Error fetching user: {str(e)}"
        })