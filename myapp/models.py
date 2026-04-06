"""
myapp/models.py
================
Demonstrates:
 - Django ORM (Active Record pattern)
 - Relational relationships: ForeignKey, ManyToMany
 - Model methods & properties
 - Meta class (ordering, verbose names)
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


# ──────────────────────────────────────────
# Category  (One-to-Many parent)
# ──────────────────────────────────────────
class Category(models.Model):
    """Hierarchical tag/category for posts."""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


# ──────────────────────────────────────────
# Tag  (Many-to-Many child)
# ──────────────────────────────────────────
class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    color = models.CharField(max_length=7, default='#007bff')   # hex colour

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


# ──────────────────────────────────────────
# Post  (main entity)
# ──────────────────────────────────────────
class Post(models.Model):
    STATUS_DRAFT = 'draft'
    STATUS_PUBLISHED = 'published'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_PUBLISHED, 'Published'),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique_for_date='published_at')
    body = models.TextField()
    author = models.ForeignKey(            # ForeignKey → Many-to-One
        User,
        on_delete=models.CASCADE,
        related_name='posts',
    )
    category = models.ForeignKey(          # Another FK
        Category,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='posts',
    )
    tags = models.ManyToManyField(         # M2M relationship
        Tag,
        blank=True,
        related_name='posts',
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
    )
    view_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
        ]

    def __str__(self):
        return self.title

    # ── Model-level business logic ──
    def publish(self):
        """Transition draft → published."""
        self.status = self.STATUS_PUBLISHED
        self.published_at = timezone.now()
        self.save(update_fields=['status', 'published_at'])

    @property
    def is_published(self):
        return self.status == self.STATUS_PUBLISHED

    def increment_views(self):
        Post.objects.filter(pk=self.pk).update(view_count=models.F('view_count') + 1)


# ──────────────────────────────────────────
# Comment  (FK to Post, FK to User)
# ──────────────────────────────────────────
class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'Comment by {self.author} on "{self.post}"'


# ──────────────────────────────────────────
# UserProfile  (One-to-One extension of User)
# ──────────────────────────────────────────
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True)
    avatar_url = models.URLField(blank=True)
    website = models.URLField(blank=True)

    def __str__(self):
        return f'Profile({self.user.username})'


# ──────────────────────────────────────────
# AuditLog  (tracks DB-level events)
# ──────────────────────────────────────────
class AuditLog(models.Model):
    ACTION_CREATE = 'CREATE'
    ACTION_UPDATE = 'UPDATE'
    ACTION_DELETE = 'DELETE'
    ACTION_CHOICES = [
        (ACTION_CREATE, 'Create'),
        (ACTION_UPDATE, 'Update'),
        (ACTION_DELETE, 'Delete'),
    ]

    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=50)
    object_id = models.PositiveIntegerField(null=True)
    detail = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f'{self.action} {self.model_name}#{self.object_id} by {self.user}'