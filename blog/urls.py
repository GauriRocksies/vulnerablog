"""
VulneraBlog URL patterns
"""

from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Authentication
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    # Password reset (Django built-in views, custom templates)
    path('password-reset/',
        auth_views.PasswordResetView.as_view(
            template_name='registration/password_reset.html',
            email_template_name='registration/password_reset_email.txt',
            subject_template_name='registration/password_reset_subject.txt',
        ),
        name='password_reset'),
    path('password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='registration/password_reset_done.html',
        ),
        name='password_reset_done'),
    path('password-reset/confirm/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='registration/password_reset_confirm.html',
        ),
        name='password_reset_confirm'),
    path('password-reset/complete/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='registration/password_reset_complete.html',
        ),
        name='password_reset_complete'),

    # Main pages
    path('', views.home_view, name='home'),
    path('explore/', views.explore_view, name='explore'),
    path('bookmarks/', views.bookmarks_view, name='bookmarks'),

    # Posts
    path('post/<int:pk>/', views.post_detail_view, name='post_detail'),
    path('post/upload/', views.upload_post_view, name='upload_post'),
    path('post/<int:pk>/edit/', views.edit_post_view, name='edit_post'),
    path('post/<int:pk>/delete/', views.delete_post_view, name='delete_post'),

    # AJAX toggles
    path('post/<int:pk>/like/', views.like_post_view, name='like_post'),
    path('post/<int:pk>/bookmark/', views.bookmark_post_view, name='bookmark_post'),
    path('comment/<int:pk>/like/', views.like_comment_view, name='like_comment'),

    # Profile (edit_profile MUST come before profile/<str:username>/)
    path('profile/edit/me/', views.edit_profile_view, name='edit_profile'),
    path('profile/<str:username>/', views.profile_view, name='profile'),
    path('user/<str:username>/follow/', views.follow_user_view, name='follow_user'),
]