from django.urls import path
from .views import homepage_view, signup_view

urlpatterns = [
    path('', homepage_view, name='home'),
    path('signup/', signup_view, name='signup'),
]
