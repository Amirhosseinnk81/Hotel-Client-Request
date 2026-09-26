"""
Who may call the PMS webhook. Not a user, so not JWT: the PMS proves itself
with a shared key, and optionally by signing the body.

  X-PMS-Key        settings.PMS_SHARED_KEY, compared in constant time
  X-PMS-Signature  optional: "sha256=<hex>", HMAC of the raw body with
                   settings.PMS_HMAC_SECRET. Required as soon as that
                   secret is set, so turning it on can't be forgotten.

With no PMS_SHARED_KEY configured the endpoint refuses everything — an
integration that is not set up must not sit open.
"""

import hashlib
import hmac

from django.conf import settings
from rest_framework.permissions import BasePermission


def _constant_time_equals(a, b):
    return hmac.compare_digest(str(a or ""), str(b or ""))


def signature_matches(raw_body, provided):
    secret = getattr(settings, "PMS_HMAC_SECRET", "")
    if not secret:
        return True  # signing not in use
    expected = hmac.new(secret.encode(), raw_body or b"", hashlib.sha256).hexdigest()
    supplied = (provided or "").split("=", 1)[-1].strip()
    return _constant_time_equals(expected, supplied)


class IsPmsClient(BasePermission):
    message = "Invalid PMS credentials."

    def has_permission(self, request, view):
        key = getattr(settings, "PMS_SHARED_KEY", "")
        if not key:
            self.message = "The PMS integration is not configured (PMS_SHARED_KEY)."
            return False
        if not _constant_time_equals(key, request.headers.get("X-PMS-Key")):
            return False
        if not signature_matches(request.body, request.headers.get("X-PMS-Signature")):
            self.message = "Invalid PMS signature."
            return False
        return True
