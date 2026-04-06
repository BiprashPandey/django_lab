"""
myapp/views.py
==============
Demonstrates:
 - Function-Based Views (FBV)
 - Class-Based Views (CBV) – ListView, DetailView, CreateView, UpdateView, DeleteView
 - Authentication decorators: @login_required, @permission_required
 - Request/Response cycle: HttpRequest, HttpResponse, JsonResponse, redirect
 - Session reading/writing
 - Form processing (GET/POST pattern, CSRF)
 - ORM CRUD: create, filter, get, update, delete, select_related, prefetch_related
 - Pagination
 - Cookie handling
"""

import logging
from datetime import datetime

from django.contrib import messages
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.models import User
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Count
from django.http import (HttpResponse, JsonResponse, HttpResponseForbidden,
                          HttpResponseNotFound)
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import (ListView, DetailView, CreateView,
                                   UpdateView, DeleteView)

from .forms import (PostForm, CommentForm, ContactForm, SearchForm,
                    UserRegistrationForm, StyledLoginForm)
from .models import Post, Category, Tag, Comment, UserProfile, AuditLog

logger = logging.getLogger('myapp')


# ═══════════════════════════════════════════════════════════════
#  HOME – Function-Based View + Session counter
# ═══════════════════════════════════════════════════════════════
def home(request):
    """Landing page. Demonstrates session read/write."""
    # Session: track visit count
    visit_count = request.session.get('visit_count', 0) + 1
    request.session['visit_count'] = visit_count
    request.session['last_visited'] = datetime.now().isoformat()

    featured = Post.objects.filter(status='published').select_related('author', 'category')[:3]
    categories = Category.objects.annotate(post_count=Count('posts'))

    context = {
        'featured_posts': featured,
        'categories': categories,
        'visit_count': visit_count,
    }

    # Cookie: set a theme preference if not already set
    response = render(request, 'myapp/home.html', context)
    if 'theme' not in request.COOKIES:
        response.set_cookie('theme', 'light', max_age=60 * 60 * 24 * 30)  # 30 days
    return response


# ═══════════════════════════════════════════════════════════════
#  AUTHENTICATION – Register, Login, Logout
# ═══════════════════════════════════════════════════════════════
def register(request):
    """User registration: demonstrates form handling + ORM create."""
    if request.user.is_authenticated:
        return redirect('myapp:dashboard')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.create(user=user)           # ORM CREATE
            AuditLog.objects.create(                        # ORM CREATE (audit)
                user=user, action='CREATE', model_name='User', object_id=user.pk,
                detail=f'New user registered: {user.username}',
                ip_address=_get_client_ip(request),
            )
            login(request, user)
            messages.success(request, f'Welcome, {user.first_name}! Your account has been created.')
            logger.info('New user registered: %s', user.username)
            return redirect('myapp:dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserRegistrationForm()

    return render(request, 'myapp/register.html', {'form': form})


def user_login(request):
    """Login view: demonstrates authenticate() + session creation."""
    if request.user.is_authenticated:
        return redirect('myapp:dashboard')

    if request.method == 'POST':
        form = StyledLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            # Store login time in session
            request.session['login_time'] = datetime.now().isoformat()
            messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
            logger.info('User logged in: %s from %s', user.username, _get_client_ip(request))
            next_url = request.GET.get('next', reverse('myapp:dashboard'))
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = StyledLoginForm(request)

    return render(request, 'myapp/login.html', {'form': form})


@login_required
def user_logout(request):
    """Logout: destroys session."""
    username = request.user.username
    logout(request)
    messages.info(request, 'You have been logged out.')
    logger.info('User logged out: %s', username)
    return redirect('myapp:home')


# ═══════════════════════════════════════════════════════════════
#  DASHBOARD – login required FBV
# ═══════════════════════════════════════════════════════════════
@login_required
def dashboard(request):
    """User dashboard: ORM read with aggregations, session data."""
    user_posts = Post.objects.filter(author=request.user).order_by('-created_at')
    user_comments = Comment.objects.filter(author=request.user).select_related('post')[:5]

    context = {
        'user_posts': user_posts,
        'user_comments': user_comments,
        'total_posts': user_posts.count(),
        'published_count': user_posts.filter(status='published').count(),
        'draft_count': user_posts.filter(status='draft').count(),
        'login_time': request.session.get('login_time', 'N/A'),
        'visit_count': request.session.get('visit_count', 0),
    }
    return render(request, 'myapp/dashboard.html', context)


# ═══════════════════════════════════════════════════════════════
#  POST LIST – Class-Based View (ListView)
# ═══════════════════════════════════════════════════════════════
class PostListView(ListView):
    """Demonstrates CBV ListView with custom queryset, pagination, search."""
    model = Post
    template_name = 'myapp/post_list.html'
    context_object_name = 'posts'
    paginate_by = 5

    def get_queryset(self):
        queryset = (Post.objects
                    .filter(status='published')
                    .select_related('author', 'category')
                    .prefetch_related('tags')
                    .order_by('-created_at'))

        # Search / filter
        query = self.request.GET.get('query')
        category_id = self.request.GET.get('category')
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) | Q(body__icontains=query)
            )
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        return queryset

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['search_form'] = SearchForm(self.request.GET)
        ctx['categories'] = Category.objects.all()
        return ctx


# ═══════════════════════════════════════════════════════════════
#  POST DETAIL – Class-Based View (DetailView)
# ═══════════════════════════════════════════════════════════════
class PostDetailView(DetailView):
    model = Post
    template_name = 'myapp/post_detail.html'
    context_object_name = 'post'

    def get_object(self):
        post = get_object_or_404(Post, pk=self.kwargs['pk'], status='published')
        post.increment_views()          # ORM atomic update
        return post

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['comments'] = self.object.comments.filter(is_approved=True).select_related('author')
        ctx['comment_form'] = CommentForm()
        ctx['related_posts'] = (Post.objects
                                 .filter(category=self.object.category, status='published')
                                 .exclude(pk=self.object.pk)[:3])
        return ctx

    def post(self, request, *args, **kwargs):
        """Handle comment submission on the same URL (GET = view, POST = comment)."""
        if not request.user.is_authenticated:
            messages.warning(request, 'Please log in to leave a comment.')
            return redirect('myapp:login')
        post = self.get_object()
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.author = request.user
            comment.save()
            messages.success(request, 'Comment submitted and awaiting approval.')
        else:
            messages.error(request, 'Could not submit comment.')
        return redirect('myapp:post_detail', pk=post.pk)


# ═══════════════════════════════════════════════════════════════
#  POST CREATE / UPDATE / DELETE – CBV with LoginRequired mixin
# ═══════════════════════════════════════════════════════════════
class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = 'myapp/post_form.html'
    success_url = reverse_lazy('myapp:dashboard')

    def form_valid(self, form):
        form.instance.author = self.request.user
        response = super().form_valid(form)
        AuditLog.objects.create(
            user=self.request.user, action='CREATE', model_name='Post',
            object_id=form.instance.pk, detail=f'Post "{form.instance.title}" created.',
            ip_address=_get_client_ip(self.request),
        )
        messages.success(self.request, 'Post created successfully!')
        return response


class PostUpdateView(LoginRequiredMixin, UpdateView):
    model = Post
    form_class = PostForm
    template_name = 'myapp/post_form.html'
    success_url = reverse_lazy('myapp:dashboard')

    def get_object(self):
        post = get_object_or_404(Post, pk=self.kwargs['pk'])
        if post.author != self.request.user and not self.request.user.is_staff:
            raise PermissionError("You may only edit your own posts.")
        return post

    def form_valid(self, form):
        response = super().form_valid(form)
        AuditLog.objects.create(
            user=self.request.user, action='UPDATE', model_name='Post',
            object_id=form.instance.pk, detail=f'Post "{form.instance.title}" updated.',
            ip_address=_get_client_ip(self.request),
        )
        messages.success(self.request, 'Post updated successfully!')
        return response


class PostDeleteView(LoginRequiredMixin, DeleteView):
    model = Post
    template_name = 'myapp/post_confirm_delete.html'
    success_url = reverse_lazy('myapp:dashboard')

    def form_valid(self, form):
        AuditLog.objects.create(
            user=self.request.user, action='DELETE', model_name='Post',
            object_id=self.object.pk, detail=f'Post "{self.object.title}" deleted.',
            ip_address=_get_client_ip(self.request),
        )
        messages.success(self.request, 'Post deleted.')
        return super().form_valid(form)


# ═══════════════════════════════════════════════════════════════
#  CONTACT – Plain Form + Session flash data
# ═══════════════════════════════════════════════════════════════
def contact(request):
    """Demonstrates plain (non-model) form + messages framework."""
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            # Store last contact data in session
            request.session['last_contact'] = {
                'name': form.cleaned_data['name'],
                'subject': form.cleaned_data['subject'],
                'sent_at': datetime.now().isoformat(),
            }
            messages.success(request, 'Thank you! Your message has been received.')
            logger.info('Contact form submitted by %s', form.cleaned_data['email'])
            return redirect('myapp:contact')
        else:
            messages.error(request, 'Please fix the form errors below.')
    else:
        form = ContactForm()

    last_contact = request.session.get('last_contact')
    return render(request, 'myapp/contact.html', {'form': form, 'last_contact': last_contact})


# ═══════════════════════════════════════════════════════════════
#  API ENDPOINT – JsonResponse demo
# ═══════════════════════════════════════════════════════════════
def api_posts(request):
    """Simple JSON API endpoint demonstrating JsonResponse."""
    posts = (Post.objects
             .filter(status='published')
             .values('id', 'title', 'author__username', 'created_at', 'view_count')
             .order_by('-created_at')[:10])

    data = [
        {
            'id': p['id'],
            'title': p['title'],
            'author': p['author__username'],
            'created_at': p['created_at'].isoformat(),
            'view_count': p['view_count'],
        }
        for p in posts
    ]
    return JsonResponse({'count': len(data), 'posts': data})


# ═══════════════════════════════════════════════════════════════
#  ADMIN-ONLY AUDIT LOG – permission_required
# ═══════════════════════════════════════════════════════════════
@permission_required('myapp.view_auditlog', raise_exception=True)
def audit_log_view(request):
    """Only accessible by users with the view_auditlog permission."""
    logs = AuditLog.objects.select_related('user').order_by('-timestamp')[:50]
    return render(request, 'myapp/audit_log.html', {'logs': logs})


# ═══════════════════════════════════════════════════════════════
#  COOKIE DEMO – explicit cookie read/write
# ═══════════════════════════════════════════════════════════════
def set_theme(request, theme):
    """Toggle site theme via cookie."""
    if theme not in ('light', 'dark'):
        return HttpResponseForbidden('Invalid theme.')
    response = redirect(request.META.get('HTTP_REFERER', '/'))
    response.set_cookie('theme', theme, max_age=60 * 60 * 24 * 365)
    return response


# ═══════════════════════════════════════════════════════════════
#  CUSTOM ERROR VIEWS
# ═══════════════════════════════════════════════════════════════
def handler404(request, exception):
    return render(request, 'myapp/404.html', status=404)


def handler500(request):
    return render(request, 'myapp/500.html', status=500)


# ───── Helper ─────
def _get_client_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    return x_forwarded.split(',')[0] if x_forwarded else request.META.get('REMOTE_ADDR')