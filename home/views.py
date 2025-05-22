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
from dateutil import parser
from django.shortcuts import redirect
from zoneinfo import ZoneInfo


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
def fetch_chat_messages_view(request):
    user_id = request.session.get("user_id")
    receiver_id = request.GET.get("receiver_id")
    before_id = request.GET.get("before_id")  # Optional: for pagination
    limit = int(request.GET.get("limit", 10))  # Default to 10

    if not user_id or not receiver_id:
        return JsonResponse({'status': 'error', 'message': 'Missing user or receiver'}, status=400)

    try:
        # Build base filter for both directions of the convo
        query = (
            supabase
            .table("chats")
            .select("*")
            .or_(
                f"and(sender_id.eq.{user_id},receiver_id.eq.{receiver_id}),"
                f"and(sender_id.eq.{receiver_id},receiver_id.eq.{user_id})"
            )
        )

        # Apply 'before_id' for pagination if provided
        if before_id:
            query = query.lt("id", int(before_id))

        # Sort by newest first, limit to 10
        messages_response = query.order("id", desc=True).limit(limit).execute()
        manila = timezone("Asia/Manila")

        messages = []
        for msg in reversed(messages_response.data):  # Reverse to show oldest to newest
            local_time = datetime.datetime.fromisoformat(
                msg["created_at"].replace("Z", "+00:00")
            ).astimezone(manila).strftime("%b %d, %Y %I:%M %p")

            messages.append({
                "id": msg["id"],
                "sender_id": msg["sender_id"],
                "receiver_id": msg["receiver_id"],
                "message": msg["message"],
                "time": local_time,
                "is_you": msg["sender_id"] == user_id
            })

        return JsonResponse(messages, safe=False)

    except Exception as e:
        print("Error fetching chat messages:", e)
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@csrf_exempt
def send_chat_message_view(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Only POST allowed."}, status=405)

    try:
        import json
        data = json.loads(request.body.decode("utf-8"))

        sender_id = request.session.get("user_id")
        receiver_id = data.get("receiver_id")
        message = data.get("message", "").strip()

        if not sender_id or not receiver_id or not message:
            return JsonResponse({"status": "error", "message": "Missing fields."}, status=400)

        # Insert new chat record into Supabase
        supabase.table("chats").insert({
            "sender_id": sender_id,
            "receiver_id": receiver_id,
            "message": message
        }).execute()

        return JsonResponse({"status": "success", "message": "Message sent."})

    except Exception as e:
        print("Send message failed:", e)
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@csrf_exempt
def create_post_view(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Only POST method allowed."}, status=405)

    user_id = request.session.get("user_id")
    if not user_id:
        return JsonResponse({"status": "error", "message": "User not authenticated."}, status=401)

    content = request.POST.get("content", "").strip()
    media_file = request.FILES.get("media")

    if not content:
        return JsonResponse({"status": "error", "message": "Content cannot be empty."}, status=400)

    media_url = ""

    # ✅ Upload to Supabase Storage if media exists
    if media_file:
        try:
            file_ext = os.path.splitext(media_file.name)[-1]
            unique_path = f"posts/{uuid.uuid4()}{file_ext}"
            file_bytes = media_file.read()

            supabase.storage.from_("files").upload(
                path=unique_path,
                file=file_bytes,
                file_options={"content-type": media_file.content_type}
            )

            media_url = supabase.storage.from_("files").get_public_url(unique_path)

        except Exception as e:
            print("Media upload failed:", e)
            return JsonResponse({"status": "error", "message": "Failed to upload media."}, status=500)

    # ✅ Insert into `posts` table
    try:
        supabase.table("posts").insert({
            "user_id": user_id,
            "content": content,
            "media_url": media_url,
            "created_at": datetime.datetime.utcnow().isoformat()
        }).execute()

        return JsonResponse({"status": "success", "message": "Post created."})

    except Exception as e:
        print("Database insert failed:", e)
        return JsonResponse({"status": "error", "message": "Failed to save post."}, status=500)
    


@csrf_exempt
def searched_profile_view(request, username):
    try:
        # Fetch receiver account by username
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
        user_id = request.session.get("user_id")

        # Handle chat message sending
        if request.method == "POST":
            sender_id = user_id
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

            return redirect("searched_profile", username=username)

        # Fetch latest 5 posts for that user
        posts_response = (
            supabase
            .table("posts")
            .select("*")
            .eq("user_id", receiver_data["user_id"])
            .order("created_at", desc=True)
            .limit(5)
            .execute()
        )

        manila = ZoneInfo("Asia/Manila")
        raw_posts = posts_response.data if posts_response.data else []
        posts = []

        for post in raw_posts:
            try:
                post_id = str(post.get("id", ""))
                # Safe timestamp parsing
                try:
                    post["created_at"] = parser.isoparse(post.get("created_at")).astimezone(manila)
                except Exception as e:
                    print(f"Timestamp parse failed for post {post_id}:", e)
                    post["created_at"] = django_now()

                # Default values
                post["like_count"] = 0
                post["liked_by_user"] = False
                post["comment_count"] = 0

                # Count likes
                try:
                    likes = supabase.table("likes").select("id").eq("post_id", post_id).execute()
                    post["like_count"] = len(likes.data or [])
                except Exception as e:
                    print(f"Like count failed for post {post_id}:", e)

                # Check if current user already liked this post
                if user_id:
                    try:
                        liked = supabase.table("likes").select("id").eq("post_id", post_id).eq("user_id", user_id).execute()
                        post["liked_by_user"] = bool(liked.data)
                    except Exception as e:
                        print(f"Like check failed for post {post_id}:", e)

                # Count comments
                try:
                    comments = supabase.table("comments").select("id").eq("post_id", post_id).execute()
                    post["comment_count"] = len(comments.data or [])
                except Exception as e:
                    print(f"Comment count failed for post {post_id}:", e)

                posts.append(post)

            except Exception as post_error:
                print(f"Post enrichment failed: {post_error}")

        return render(request, "home/searched_profile.html", {
            "user": receiver_data,
            "posts": posts
        })

    except Exception as e:
        print("Main view failed:", e)
        return render(request, "home/searched_profile.html", {
            "error": f"Error fetching user: {str(e)}"
        })


@csrf_exempt
def load_user_posts_view(request, username):
    try:
        offset = int(request.GET.get("offset", 0))
        limit = 5

        # Find the user by username
        user_response = (
            supabase
            .table("accounts")
            .select("user_id")
            .eq("username", username)
            .single()
            .execute()
        )
        if not user_response.data:
            return JsonResponse({"error": "User not found"}, status=404)

        user_id = user_response.data["user_id"]

        # Fetch more posts
        posts_response = (
            supabase
            .table("posts")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        return JsonResponse(posts_response.data, safe=False)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    


@csrf_exempt
def like_post_view(request, post_id):
    if request.method != "POST" or not request.session.get("user_id"):
        return JsonResponse({"status": "error", "message": "Unauthorized"}, status=401)

    user_id = request.session.get("user_id")

    try:
        # Check if user already liked
        existing = (
            supabase
            .table("likes")
            .select("id")
            .eq("user_id", user_id)
            .eq("post_id", post_id)
            .execute()
        )

        if existing.data:
            # Unlike
            supabase.table("likes").delete().eq("user_id", user_id).eq("post_id", post_id).execute()
            liked = False
        else:
            # Like
            supabase.table("likes").insert({
                "user_id": user_id,
                "post_id": post_id,
            }).execute()
            liked = True

        # Count updated likes
        count_result = (
            supabase.table("likes")
            .select("id", count="exact")
            .eq("post_id", post_id)
            .execute()
        )
        new_count = len(count_result.data or [])

        return JsonResponse({
            "status": "success",
            "liked": liked,
            "new_count": new_count
        })

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)



@csrf_exempt
def comment_post_view(request, post_id):
    user_id = request.session.get("user_id")
    if request.method != "POST" or not user_id:
        return redirect("signin")

    comment_text = request.POST.get("comment", "").strip()
    if not comment_text:
        return redirect(request.META.get("HTTP_REFERER", "/"), status=303)

    # Insert comment
    supabase.table("comments").insert({
        "user_id": user_id,
        "post_id": post_id,
        "comment": comment_text,
    }).execute()

    return redirect(request.META.get("HTTP_REFERER", "/"), status=303)



@csrf_exempt
def get_post_comments(request, post_id):
    if request.method == "GET":
        try:
            comments = (
                supabase
                .table("comments")
                .select("id, comment, created_at, user_id")  # ✅ remove invalid join
                .eq("post_id", post_id)
                .order("created_at", desc=False)
                .execute()
            )
            return JsonResponse(comments.data, safe=False)
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    
@csrf_exempt
def get_user_info_view(request, user_id):
    if request.method == "GET":
        try:
            user = (
                supabase
                .table("accounts")
                .select("full_name, profile_url")
                .eq("user_id", user_id)
                .single()
                .execute()
            )
            return JsonResponse(user.data)
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

