from django.shortcuts import render, get_object_or_404
from .models import Post, Profile
from django.contrib.auth.models import User


def main_feed(request):
    posts = Post.objects.all().order_by("-created_at")
    return render(request, "main_feed.html", {"posts": posts})


def post_detail(request, id):
    post = get_object_or_404(Post, id=id)
    return render(request, "post_detail.html", {"post": post})


def user_profile(request, username):
    user = get_object_or_404(User, username=username)
    posts = Post.objects.filter(author=user)

    return render(request, "user_profile.html", {
        "profile_user": user,
        "posts": posts
    })


def login_page(request):
    return render(request, "login.html")


def register_page(request):
    return render(request, "register.html")