"""
myapp/urls.py
=============
Demonstrates:
 - URL namespacing (app_name = 'myapp')
 - path() with converters: <int:pk>, <str:theme>
 - re_path() for regex patterns
 - Named URL patterns used with reverse() / {% url %} in templates
 - Grouping FBVs and CBVs together
"""

from django.urls import path, re_path
from . import views

app_name = 'myapp'

urlpatterns = [
    # ── Home ──────────────────────────────────────────────────
    path('', views.home, name='home'),

    # ── Authentication ────────────────────────────────────────
    path('register/', views.register, name='register'),
    path('login/',    views.user_login, name='login'),
    path('logout/',   views.user_logout, name='logout'),

    # ── Dashboard ─────────────────────────────────────────────
    path('dashboard/', views.dashboard, name='dashboard'),

    # ── Posts (CBVs) ──────────────────────────────────────────
    path('posts/',                  views.PostListView.as_view(),   name='post_list'),
    path('posts/<int:pk>/',         views.PostDetailView.as_view(), name='post_detail'),
    path('posts/new/',              views.PostCreateView.as_view(), name='post_create'),
    path('posts/<int:pk>/edit/',    views.PostUpdateView.as_view(), name='post_update'),
    path('posts/<int:pk>/delete/',  views.PostDeleteView.as_view(), name='post_delete'),

    # ── Contact (FBV) ─────────────────────────────────────────
    path('contact/', views.contact, name='contact'),

    # ── API ───────────────────────────────────────────────────
    path('api/posts/', views.api_posts, name='api_posts'),

    # ── Admin extras ──────────────────────────────────────────
    path('audit/', views.audit_log_view, name='audit_log'),

    # ── Cookie / Theme toggle ─────────────────────────────────
    path('theme/<str:theme>/', views.set_theme, name='set_theme'),

    # ── Regex example: match slug-style category paths ────────
    re_path(r'^category/(?P<slug>[\w-]+)/$', views.PostListView.as_view(), name='category'),
]