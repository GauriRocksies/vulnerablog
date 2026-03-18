from django.urls import path
from . import views

urlpatterns = [
    path("", views.main_feed, name="feed"),
    path("post/<int:id>/", views.post_detail, name="post"),
    path("user/<str:username>/", views.user_profile, name="profile"),
    path("login/", views.login_page, name="login"),
    path("register/", views.register_page, name="register"),
]