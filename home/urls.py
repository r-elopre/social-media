from django.urls import path
from .views import homepage_view, signup_view
from .views import homepage_view, signup_view, signin_view
from .views import search_users_view
from .views import searched_profile_view
from .views import logout_view
from .views import fetch_chat_messages_view
from .views import send_chat_message_view
from .views import create_post_view
from .views import load_user_posts_view
from .views import like_post_view, comment_post_view
from .views import get_post_comments
from .views import get_user_info_view
from .views import global_posts_view 
from .views import toggle_follow_view



urlpatterns = [
    path('', signin_view, name='signin'),
    path('home/', homepage_view, name='home'),
    path('signup/', signup_view, name='signup'),
    path('search-users/', search_users_view, name='search_users'),
    path('user-profile/<str:username>/', searched_profile_view, name='searched_profile'),
    path('logout/', logout_view, name='logout'),
    path('chat/messages/', fetch_chat_messages_view, name='fetch_chat_messages'),
    path('chat/send/', send_chat_message_view, name='send_chat_message'),
    path("create-post/", create_post_view, name="create_post"),
    path("user-posts/<str:username>/", load_user_posts_view, name="load_user_posts"),
    path("like-post/<int:post_id>/", like_post_view, name="like_post"),
    path("comment-post/<int:post_id>/", comment_post_view, name="comment_post"),
    path("get-post-comments/<int:post_id>/", get_post_comments, name="get_post_comments"),
    path("get-user-info/<str:user_id>/", get_user_info_view, name="get_user_info"),
    path("global-posts/", global_posts_view, name="global_posts"),
    path("toggle-follow/", toggle_follow_view, name="toggle_follow"),

]

