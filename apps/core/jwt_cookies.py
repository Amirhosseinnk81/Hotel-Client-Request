"""
Shared helpers for issuing the refresh token as an httpOnly cookie instead
of returning it in the JSON response body.

Design (see docs — Phase 2, Stage 2.6, JWT/localStorage security review):

- The REFRESH token (long-lived, most damaging if stolen) is set ONLY via
  Set-Cookie, httponly=True. It is never present in any JSON response body,
  so frontend JavaScript never has a way to read or persist it — this is
  what actually closes the XSS-exfiltration gap that localStorage had.
- The ACCESS token (short-lived, 15 min by default) is still returned in
  the JSON body and used as a normal `Authorization: Bearer <token>` header
  by the frontend, exactly as before — it is kept in memory only on the
  frontend (never localStorage), so the exposure window on a successful XSS
  is bounded by the access-token lifetime instead of lasting for weeks.
- SameSite=Lax (rather than Django's CSRF-token machinery) is the CSRF
  mitigation for the refresh/logout endpoints: Lax cookies are not attached
  by the browser to cross-site POST requests, which is exactly the request
  method both endpoints use. The cookie's `path` is also scoped to the auth
  prefix so it is never sent on ordinary API calls that don't need it.
"""

from django.conf import settings

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth/"


def set_refresh_cookie(response, refresh_token: str) -> None:
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        refresh_token,
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        httponly=True,
        secure=settings.JWT_COOKIE_SECURE,
        samesite="Lax",
        path=REFRESH_COOKIE_PATH,
    )


def clear_refresh_cookie(response) -> None:
    response.delete_cookie(REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)
