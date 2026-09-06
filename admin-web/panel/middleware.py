import time

import jwt
from django.conf import settings
from django.http import HttpResponse


class CloudflareAccessMiddleware:
    """Reject requests that did not traverse the configured Cloudflare Access app."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.jwks = None
        self.jwks_url = settings.CF_ACCESS_JWKS or (
            f"https://{settings.CF_ACCESS_TEAM_DOMAIN}/cdn-cgi/access/certs"
            if settings.CF_ACCESS_TEAM_DOMAIN else ""
        )

    def __call__(self, request):
        if request.path == "/healthz/" and request.META.get("REMOTE_ADDR") in {"127.0.0.1", "::1"}:
            return self.get_response(request)
        if not settings.CF_ACCESS_REQUIRED:
            request.cf_access_email = settings.OWNER_EMAIL
            return self.get_response(request)
        if not self.jwks_url or not settings.CF_ACCESS_AUD or not settings.CF_ACCESS_TEAM_DOMAIN:
            return HttpResponse("Cloudflare Access is not configured", status=503)
        token = request.headers.get("Cf-Access-Jwt-Assertion", "") or request.COOKIES.get("CF_Authorization", "")
        if not token:
            return HttpResponse("Cloudflare Access authentication required", status=403)
        try:
            if self.jwks is None:
                self.jwks = jwt.PyJWKClient(self.jwks_url, cache_jwk_set=True, lifespan=3600)
            signing_key = self.jwks.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=settings.CF_ACCESS_AUD,
                issuer=f"https://{settings.CF_ACCESS_TEAM_DOMAIN}",
                options={"require": ["exp", "iat", "aud", "iss", "email"]},
            )
        except Exception:
            return HttpResponse("Invalid Cloudflare Access assertion", status=403)
        email = str(claims.get("email", "")).lower()
        if email != settings.OWNER_EMAIL:
            return HttpResponse("Owner access only", status=403)
        request.cf_access_email = email
        return self.get_response(request)


class AdminSecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'self'; "
            "img-src 'self' data: https://2264.eu; style-src 'self' https://2264.eu; script-src 'self'; "
            "connect-src 'self'; object-src 'none'"
        )
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
        response.headers["Cache-Control"] = "no-store"
        return response
