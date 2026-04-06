"""
myapp/admin.py
==============
Registers models with the Django admin site.
Demonstrates:
 - ModelAdmin customisation
 - list_display, list_filter, search_fields
 - actions (custom admin action)
 - inline admins
"""

from django.contrib import admin
from .models import Post, Category, Tag, Comment, UserProfile, AuditLog


class CommentInline(admin.TabularInline):
    """Show comments inline on the Post admin page."""
    model = Comment
    extra = 0
    readonly_fields = ('author', 'created_at')


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'status', 'category', 'view_count', 'created_at')
    list_filter = ('status', 'category', 'tags')
    search_fields = ('title', 'body', 'author__username')
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    inlines = [CommentInline]

    # Custom admin action
    @admin.action(description='Publish selected posts')
    def make_published(self, request, queryset):
        updated = queryset.filter(status='draft').count()
        queryset.filter(status='draft').update(status='published')
        self.message_user(request, f'{updated} post(s) published successfully.')

    actions = [make_published]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'color')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('author', 'post', 'is_approved', 'created_at')
    list_filter = ('is_approved',)
    actions = ['approve_comments']

    @admin.action(description='Approve selected comments')
    def approve_comments(self, request, queryset):
        queryset.update(is_approved=True)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'website')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'model_name', 'object_id', 'user', 'ip_address', 'timestamp')
    list_filter = ('action', 'model_name')
    readonly_fields = ('user', 'action', 'model_name', 'object_id', 'detail',
                       'timestamp', 'ip_address')