"""
myproject/urls.py  –  Root URL Configuration
All application routes are namespaced under 'myapp'.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Django admin site
    path('admin/', admin.site.urls),

    # All application URLs delegated to myapp/urls.py
    path('', include('myapp.urls', namespace='myapp')),
]

# Serve static/media in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)