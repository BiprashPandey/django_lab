"""
myapp/middleware.py
===================
Custom middleware demonstrating:
 - Request / Response hooks (__call__ pattern)
 - process_view() for pre-view logic
 - process_exception() for error handling
 - Structured logging
 - Maintenance mode
 - Simple IP-based rate limiting
"""

import logging
import time
from collections import defaultdict
from django.conf import settings
from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('myapp.middleware')


# ──────────────────────────────────────────────────────────────
# 1.  Request Logging Middleware
# ──────────────────────────────────────────────────────────────
class RequestLoggingMiddleware:
    """
    Logs every HTTP request with:
     - method, path, status code, response time, authenticated user
    """

    def __init__(self, get_response):
        self.get_response = get_response   # next middleware / view

    def __call__(self, request):
        start_time = time.monotonic()

        # ── Before the view ──
        ip = self._get_ip(request)
        user = getattr(request, 'user', None)
        username = user.username if (user and user.is_authenticated) else 'anonymous'

        # ── Call the next middleware / view ──
        response = self.get_response(request)

        # ── After the view ──
        elapsed_ms = (time.monotonic() - start_time) * 1000
        logger.info(
            '[%s] %s %s → %s | %.1f ms | user=%s',
            ip, request.method, request.path,
            response.status_code, elapsed_ms, username,
        )
        # Attach timing header for debugging
        response['X-Response-Time-ms'] = f'{elapsed_ms:.1f}'
        return response

    @staticmethod
    def _get_ip(request):
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        return x_forwarded.split(',')[0] if x_forwarded else request.META.get('REMOTE_ADDR', '?')


# ──────────────────────────────────────────────────────────────
# 2.  Maintenance Mode Middleware
# ──────────────────────────────────────────────────────────────
class MaintenanceModeMiddleware:
    """
    Returns a 503 page when settings.MAINTENANCE_MODE = True.
    Superusers bypass the maintenance page so admins can still work.
    """

    MAINTENANCE_HTML = """
    <html><body style="font-family:sans-serif;text-align:center;padding:60px">
    <h1>🔧 Maintenance in Progress</h1>
    <p>We'll be back shortly. Thank you for your patience.</p>
    </body></html>
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if getattr(settings, 'MAINTENANCE_MODE', False):
            user = getattr(request, 'user', None)
            if not (user and user.is_superuser):
                logger.warning('Maintenance mode – blocked request to %s', request.path)
                return HttpResponse(self.MAINTENANCE_HTML, status=503,
                                    content_type='text/html')
        return self.get_response(request)


# ──────────────────────────────────────────────────────────────
# 3.  Rate Limiting Middleware
# ──────────────────────────────────────────────────────────────
class RateLimitMiddleware:
    """
    Very simple in-memory IP rate limiter.
    Limits each IP to MAX_REQUESTS per WINDOW_SECONDS.
    NOTE: For production use a Redis-backed solution (django-ratelimit).
    """

    MAX_REQUESTS = 100
    WINDOW_SECONDS = 60

    # Shared state across requests (in-process only)
    _request_counts: dict = defaultdict(list)

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
        now = time.time()

        # Purge old timestamps
        self._request_counts[ip] = [
            t for t in self._request_counts[ip]
            if now - t < self.WINDOW_SECONDS
        ]

        if len(self._request_counts[ip]) >= self.MAX_REQUESTS:
            logger.warning('Rate limit exceeded for IP %s', ip)
            return HttpResponse(
                '{"error": "Too many requests. Please slow down."}',
                status=429,
                content_type='application/json',
            )

        self._request_counts[ip].append(now)
        return self.get_response(request)


# ──────────────────────────────────────────────────────────────
# 4.  Exception Logging Middleware  (uses MiddlewareMixin for
#     older-style process_exception hook)
# ──────────────────────────────────────────────────────────────
class ExceptionLoggingMiddleware(MiddlewareMixin):
    """~
    Catches any unhandled exception, logs the full traceback,
    then re-raises so Django's normal error handling takes over.
    """

    def process_exception(self, request, exception):
        logger.exception(
            'Unhandled exception on %s %s: %s',
            request.method, request.path, exception,
        )
        # Return None → let Django render 500 page / DEBUG traceback
        return None

    def process_view(self, request, view_func, view_args, view_kwargs):
        """
        process_view fires just before Django calls the view.
        Here we simply stamp the view name onto the request object
        so other middleware / templates can read it.
        """
        request.current_view = view_func.__name__
        return None   # None = continue processing