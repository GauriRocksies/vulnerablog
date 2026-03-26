"""
VulneraBlog Views
All view logic for the platform.
"""

import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Q, Count

from .models import User, Post, Comment, Follow, Bookmark, Tag
from .forms import LoginForm, RegisterForm, PostForm, CommentForm, ProfileEditForm


# ──────────────────────────────────────────────
# AUTH VIEWS
# ──────────────────────────────────────────────

def login_view(request):
    """Handle user login via user_id_code + password."""
    if request.user.is_authenticated:
        return redirect('home')

    form = LoginForm()

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user_id_code = form.cleaned_data['user_id_code']
            password = form.cleaned_data['password']
            user = authenticate(request, user_id_code=user_id_code, password=password)
            if user:
                login(request, user)
                next_url = request.GET.get('next', 'home')
                return redirect(next_url)
            else:
                messages.error(request, 'Invalid User ID or password. Please try again.')

    return render(request, 'blog/login.html', {'form': form})


def register_view(request):
    """Handle new user registration."""
    if request.user.is_authenticated:
        return redirect('home')

    form = RegisterForm()

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(
                request,
                f'Account created! Your User ID is: {user.user_id_code}. Please save it — you need it to log in.'
            )
            return redirect('login')

    return render(request, 'blog/register.html', {'form': form})


def logout_view(request):
    """Log out the current user."""
    logout(request)
    return redirect('login')


# ──────────────────────────────────────────────
# MAIN VIEWS
# ──────────────────────────────────────────────

@login_required
def home_view(request):
    """Main feed showing all posts, paginated."""
    posts = Post.objects.all().select_related('author').prefetch_related('tags', 'likes')

    # Optional search
    query = request.GET.get('q', '')
    if query:
        posts = posts.filter(
            Q(title__icontains=query) |
            Q(content__icontains=query) |
            Q(author__username__icontains=query)
        )

    # Pagination
    paginator = Paginator(posts, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get user's liked & bookmarked post IDs for template state
    liked_ids = set(request.user.liked_posts.values_list('id', flat=True))
    bookmarked_ids = set(
        Bookmark.objects.filter(user=request.user).values_list('post_id', flat=True)
    )

    context = {
        'page_obj': page_obj,
        'liked_ids': liked_ids,
        'bookmarked_ids': bookmarked_ids,
        'query': query,
    }
    return render(request, 'blog/home.html', context)


@login_required
def explore_view(request):
    """Explore posts with category filtering."""
    category = request.GET.get('category', '')
    posts = Post.objects.all().select_related('author').prefetch_related('tags', 'likes')

    if category:
        posts = posts.filter(category=category)

    # Pagination
    paginator = Paginator(posts, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    liked_ids = set(request.user.liked_posts.values_list('id', flat=True))
    bookmarked_ids = set(
        Bookmark.objects.filter(user=request.user).values_list('post_id', flat=True)
    )

    context = {
        'page_obj': page_obj,
        'liked_ids': liked_ids,
        'bookmarked_ids': bookmarked_ids,
        'category_choices': Post.CATEGORY_CHOICES,
        'active_category': category,
    }
    return render(request, 'blog/explore.html', context)


@login_required
def post_detail_view(request, pk):
    """Display a single blog post with comments and sidebar."""
    post = get_object_or_404(Post.objects.select_related('author').prefetch_related('tags', 'likes'), pk=pk)

    # Only top-level comments; prefetch replies
    comments = post.comments.filter(parent=None).select_related('author').prefetch_related(
        'replies', 'replies__author', 'replies__likes', 'likes'
    )

    comment_form = CommentForm()

    # States for the current user
    is_liked = request.user in post.likes.all()
    is_bookmarked = Bookmark.objects.filter(user=request.user, post=post).exists()

    # Sidebar: more posts from same category
    more_posts = Post.objects.filter(
        category=post.category
    ).exclude(pk=pk).select_related('author')[:3]

    # Handle comment submission
    if request.method == 'POST':
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.post = post
            comment.author = request.user
            parent_id = request.POST.get('parent_id')
            if parent_id:
                parent = get_object_or_404(Comment, pk=parent_id)
                comment.parent = parent
            comment.save()
            messages.success(request, 'Comment posted.')
            return redirect('post_detail', pk=pk)

    context = {
        'post': post,
        'comments': comments,
        'comment_form': comment_form,
        'is_liked': is_liked,
        'is_bookmarked': is_bookmarked,
        'more_posts': more_posts,
        'engagement_count': post.likes_count + post.comments.count(),
    }
    return render(request, 'blog/post_detail.html', context)


@login_required
def upload_post_view(request):
    """Create a new blog post."""
    form = PostForm()

    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            form.save_m2m()  # applies tags without re-saving the post
            messages.success(request, 'Post published successfully!')
            return redirect('post_detail', pk=post.pk)

    context = {'form': form, 'page_title': 'Upload Post'}
    return render(request, 'blog/upload_post.html', context)


@login_required
def edit_post_view(request, pk):
    """Edit an existing blog post (author only)."""
    post = get_object_or_404(Post, pk=pk, author=request.user)

    # Pre-populate tag_names field
    existing_tags = ' '.join([f'#{tag.name}' for tag in post.tags.all()])
    form = PostForm(instance=post, initial={'tag_names': existing_tags})

    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, 'Post updated successfully!')
            return redirect('post_detail', pk=post.pk)

    context = {'form': form, 'post': post, 'page_title': 'Edit Post'}
    return render(request, 'blog/upload_post.html', context)


@login_required
@require_POST
def delete_post_view(request, pk):
    """Delete a post (author only)."""
    post = get_object_or_404(Post, pk=pk, author=request.user)
    post.delete()
    messages.success(request, 'Post deleted.')
    return redirect('home')


@login_required
def bookmarks_view(request):
    """Show the current user's bookmarked posts."""
    bookmarks = Bookmark.objects.filter(
        user=request.user
    ).select_related('post', 'post__author').prefetch_related('post__tags', 'post__likes')

    liked_ids = set(request.user.liked_posts.values_list('id', flat=True))
    bookmarked_ids = set(b.post_id for b in bookmarks)

    context = {
        'bookmarks': bookmarks,
        'liked_ids': liked_ids,
        'bookmarked_ids': bookmarked_ids,
    }
    return render(request, 'blog/bookmarks.html', context)


@login_required
def profile_view(request, username):
    """View a user's public profile with followers/following lists."""
    profile_user = get_object_or_404(User, username=username)
    posts = Post.objects.filter(author=profile_user).select_related('author').prefetch_related('tags', 'likes')

    # Check if current user is following the profile user
    is_following = Follow.objects.filter(
        follower=request.user,
        following=profile_user
    ).exists()

    # Get followers (people following this user)
    followers_list = Follow.objects.filter(
        following=profile_user
    ).select_related('follower').order_by('-created_at')[:8]

    # Get following (people this user follows)
    following_list = Follow.objects.filter(
        follower=profile_user
    ).select_related('following').order_by('-created_at')[:8]

    # Get counts
    followers_count = Follow.objects.filter(following=profile_user).count()
    following_count = Follow.objects.filter(follower=profile_user).count()
    posts_count = posts.count()

    context = {
        'profile_user': profile_user,
        'posts': posts,
        'is_following': is_following,
        'followers_list': followers_list,
        'following_list': following_list,
        'followers_count': followers_count,
        'following_count': following_count,
        'posts_count': posts_count,
        'is_own_profile': request.user == profile_user,
    }
    return render(request, 'blog/profile.html', context)


@login_required
def edit_profile_view(request):
    """Edit the current user's profile."""
    form = ProfileEditForm(instance=request.user)

    if request.method == 'POST':
        form = ProfileEditForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile', username=request.user.username)

    return render(request, 'blog/edit_profile.html', {'form': form})


# ──────────────────────────────────────────────
# AJAX / API VIEWS
# ──────────────────────────────────────────────

@login_required
@require_POST
def like_post_view(request, pk):
    """Toggle like on a post. Returns JSON."""
    post = get_object_or_404(Post, pk=pk)
    if request.user in post.likes.all():
        post.likes.remove(request.user)
        liked = False
    else:
        post.likes.add(request.user)
        liked = True

    return JsonResponse({'liked': liked, 'count': post.likes_count})


@login_required
@require_POST
def bookmark_post_view(request, pk):
    """Toggle bookmark on a post. Returns JSON."""
    post = get_object_or_404(Post, pk=pk)
    bookmark, created = Bookmark.objects.get_or_create(user=request.user, post=post)
    if not created:
        bookmark.delete()
        bookmarked = False
    else:
        bookmarked = True

    return JsonResponse({'bookmarked': bookmarked})


@login_required
@require_POST
def like_comment_view(request, pk):
    """Toggle like on a comment. Returns JSON."""
    comment = get_object_or_404(Comment, pk=pk)
    if request.user in comment.likes.all():
        comment.likes.remove(request.user)
        liked = False
    else:
        comment.likes.add(request.user)
        liked = True

    return JsonResponse({'liked': liked, 'count': comment.likes_count})


@login_required
@require_POST
def follow_user_view(request, username):
    """Toggle follow/unfollow a user. Returns JSON."""
    target_user = get_object_or_404(User, username=username)

    if target_user == request.user:
        return JsonResponse({'error': 'Cannot follow yourself'}, status=400)

    follow, created = Follow.objects.get_or_create(
        follower=request.user,
        following=target_user
    )
    if not created:
        follow.delete()
        following = False
    else:
        following = True

    return JsonResponse({
        'following': following,
        'followers_count': target_user.followers_count
    })
