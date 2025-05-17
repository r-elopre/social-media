from django.urls import path
from .views import homepage_view, signup_view
from .views import homepage_view, signup_view, signin_view

urlpatterns = [
    path('', signin_view, name='signin'),
    path('home/', homepage_view, name='home'),
    path('signup/', signup_view, name='signup'),
]

