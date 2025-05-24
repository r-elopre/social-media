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
import json

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

        # ✅ Check if current user is following the receiver
        is_following = False
        if user_id and receiver_data.get("user_id"):
            try:
                follow_check = supabase.table("follows").select("id")\
                    .eq("follower_id", user_id)\
                    .eq("following_id", receiver_data["user_id"])\
                    .execute()
                is_following = bool(follow_check.data)
            except Exception as follow_error:
                print("Follow status check failed:", follow_error)

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
            "posts": posts,
            "is_following": is_following  # ✅ Pass this to template
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
        viewer_id = request.session.get("user_id")

        # Find user by username
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

        # Fetch posts
        posts_response = (
            supabase
            .table("posts")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        enriched = []
        for post in posts_response.data:
            post_id = str(post.get("id", ""))
            post["like_count"] = 0
            post["comment_count"] = 0
            post["liked_by_user"] = False

            try:
                likes = supabase.table("likes").select("id").eq("post_id", post_id).execute()
                post["like_count"] = len(likes.data or [])
            except:
                pass

            try:
                comments = supabase.table("comments").select("id").eq("post_id", post_id).execute()
                post["comment_count"] = len(comments.data or [])
            except:
                pass

            if viewer_id:
                try:
                    liked = supabase.table("likes").select("id").eq("post_id", post_id).eq("user_id", viewer_id).execute()
                    post["liked_by_user"] = bool(liked.data)
                except:
                    pass

            enriched.append(post)

        return JsonResponse(enriched, safe=False)

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
        return JsonResponse({"status": "error", "message": "Unauthorized"}, status=401)

    try:
        data = json.loads(request.body)
        comment_text = data.get("comment", "").strip()

        if not comment_text:
            return JsonResponse({"status": "error", "message": "Empty comment"}, status=400)

        # Insert the comment
        supabase.table("comments").insert({
            "user_id": user_id,
            "post_id": post_id,
            "comment": comment_text,
        }).execute()

        return JsonResponse({"status": "success"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)



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



@csrf_exempt
def global_posts_view(request):
    try:
        offset = int(request.GET.get("offset", 0))
        limit = 5
        user_id = request.session.get("user_id")

        posts_response = (
            supabase
            .table("posts")
            .select("*")
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        posts = posts_response.data or []

        enriched_posts = []

        for post in posts:
            try:
                post_id = str(post.get("id", ""))
                user_info = (
                    supabase
                    .table("accounts")
                    .select("full_name, profile_url")
                    .eq("user_id", post["user_id"])
                    .single()
                    .execute()
                )

                post["user"] = user_info.data or {}

                # Like count
                likes = supabase.table("likes").select("id").eq("post_id", post_id).execute()
                post["like_count"] = len(likes.data or [])

                # Whether current user liked
                if user_id:
                    liked = supabase.table("likes").select("id").eq("post_id", post_id).eq("user_id", user_id).execute()
                    post["liked_by_user"] = bool(liked.data)
                else:
                    post["liked_by_user"] = False

                # Comment count
                comments = supabase.table("comments").select("id").eq("post_id", post_id).execute()
                post["comment_count"] = len(comments.data or [])

                enriched_posts.append(post)

            except Exception as post_err:
                print("Post enrichment error:", post_err)

        return JsonResponse(enriched_posts, safe=False)

    except Exception as e:
        print("Global post fetch failed:", e)
        return JsonResponse({"status": "error", "message": str(e)}, status=500)



@csrf_exempt
def toggle_follow_view(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Only POST requests are allowed."}, status=405)

    user_id = request.session.get("user_id")
    if not user_id:
        return JsonResponse({"status": "error", "message": "Authentication required."}, status=403)

    try:
        data = json.loads(request.body)
        target_username = data.get("username")
    except Exception:
        return JsonResponse({"status": "error", "message": "Invalid JSON body."}, status=400)

    if not target_username:
        return JsonResponse({"status": "error", "message": "Missing target username."}, status=400)

    try:
        # Fetch target user's ID
        target = supabase.table("accounts").select("user_id")\
            .eq("username", target_username).single().execute()

        if not target.data:
            return JsonResponse({"status": "error", "message": "Target user not found."}, status=404)

        target_id = target.data["user_id"]

        if user_id == target_id:
            return JsonResponse({"status": "error", "message": "You cannot follow yourself."}, status=400)

        # Toggle follow state
        follow_check = supabase.table("follows").select("id")\
            .eq("follower_id", user_id)\
            .eq("following_id", target_id)\
            .execute()

        if follow_check.data:
            # Unfollow
            supabase.table("follows").delete()\
                .eq("follower_id", user_id)\
                .eq("following_id", target_id)\
                .execute()
            return JsonResponse({"status": "unfollowed", "target": target_username})
        else:
            # Follow
            supabase.table("follows").insert({
                "follower_id": user_id,
                "following_id": target_id
            }).execute()
            return JsonResponse({"status": "followed", "target": target_username})

    except Exception as e:
        return JsonResponse({"status": "error", "message": "Internal server error."}, status=500)


@csrf_exempt
def get_followed_posts_view(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return JsonResponse({"status": "error", "message": "Unauthorized"}, status=403)

    try:
        # Step 1: Get list of user_ids the current user follows
        follows = supabase.table("follows").select("following_id")\
            .eq("follower_id", user_id).execute()
        following_ids = [f["following_id"] for f in follows.data]

        if not following_ids:
            return JsonResponse([], safe=False)

        # Step 2: Fetch latest posts from those users
        posts = supabase.table("posts").select("*").in_("user_id", following_ids)\
            .order("created_at", desc=True).limit(10).execute()

        enriched = []

        for post in posts.data:
            # Step 3: Fetch author profile info (including username)
            user_res = supabase.table("accounts").select("full_name", "profile_url", "username")\
                .eq("user_id", post["user_id"]).single().execute()

            if not user_res.data:
                continue

            enriched.append({
                "author_name": user_res.data["full_name"],
                "author_avatar": user_res.data["profile_url"],
                "username": user_res.data["username"],
                "content": post.get("content", "")[:120],
                "timestamp": post["created_at"]
            })

        return JsonResponse(enriched, safe=False)

    except Exception as e:
        print("Error in get_followed_posts_view:", e)
        return JsonResponse({"status": "error", "message": "Internal error"}, status=500)
