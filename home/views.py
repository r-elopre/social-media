from django.shortcuts import render


def homepage_view(request):
    return render(request, 'home/index.html')


def signup_view(request):
    return render(request, 'home/sign_up.html')
