from django.urls import path
from .views import homepage_view, signup_view
from .views import homepage_view, signup_view, signin_view
from .views import search_users_view
from .views import searched_profile_view
from .views import logout_view
from .views import fetch_chat_messages_view
from .views import send_chat_message_view




urlpatterns = [
    path('', signin_view, name='signin'),
    path('home/', homepage_view, name='home'),
    path('signup/', signup_view, name='signup'),
    path('search-users/', search_users_view, name='search_users'),
    path('user-profile/<str:username>/', searched_profile_view, name='searched_profile'),
    path('logout/', logout_view, name='logout'),
    path('chat/messages/', fetch_chat_messages_view, name='fetch_chat_messages'),
    path('chat/send/', send_chat_message_view, name='send_chat_message'),



]

