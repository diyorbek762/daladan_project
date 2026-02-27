"""
Daladan Platform — Security Headers Middleware
Adds OWASP-recommended HTTP security headers to every response.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Injects hardened HTTP security headers into every response.

    Headers applied:
      - Strict-Transport-Security (HSTS) — force HTTPS for 1 year
      - X-Content-Type-Options — prevent MIME sniffing
      - X-Frame-Options — prevent clickjacking
      - X-XSS-Protection — legacy XSS filter
      - Referrer-Policy — limit referrer leakage
      - Permissions-Policy — restrict browser APIs
      - Content-Security-Policy — basic CSP
      - Cache-Control — prevent caching of sensitive API responses
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # ── HSTS: enforce HTTPS for 1 year, include subdomains ──
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )

        # ── Prevent MIME-type sniffing ──
        response.headers["X-Content-Type-Options"] = "nosniff"

        # ── Prevent clickjacking ──
        response.headers["X-Frame-Options"] = "DENY"

        # ── Legacy XSS protection ──
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # ── Control referrer information ──
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # ── Restrict browser feature access ──
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(self), payment=()"
        )

        # ── Content Security Policy ──
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
            "https://unpkg.com https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' "
            "https://fonts.googleapis.com https://cdnjs.cloudflare.com https://unpkg.com; "
            "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
            "img-src 'self' data: https://images.unsplash.com https://*.tile.openstreetmap.org; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )

        # ── Prevent caching of API responses ──
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = (
                "no-store, no-cache, must-revalidate, max-age=0"
            )
            response.headers["Pragma"] = "no-cache"

        return response
