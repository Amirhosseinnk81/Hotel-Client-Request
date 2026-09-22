"""
SMS providers, chosen with settings.SMS_BACKEND (a dotted path) — the same
idea as Django's EMAIL_BACKEND. Switching from the fake one to a real
provider is a .env change, not a code change.
"""

import json
import logging
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)


class SmsSendError(Exception):
    """The provider refused or could not be reached; the message is retried."""


class BaseSmsBackend:
    def send(self, phone: str, body: str) -> str:
        """Send one SMS; return the provider's message id. Raise SmsSendError on failure."""
        raise NotImplementedError


class ConsoleSmsBackend(BaseSmsBackend):
    """
    The default until the hotel has a provider account: sends nothing, only
    logs the message, and reports success. The whole pipeline (queue,
    sender, retries, admin view) works end to end with it.
    """

    def send(self, phone, body):
        logger.info("SMS (console backend, not sent) to %s: %s", phone, body)
        return "console"


class KavenegarSmsBackend(BaseSmsBackend):
    """
    Kavenegar (kavenegar.com) REST API. Needs SMS_API_KEY and SMS_SENDER
    (the line number) in .env. Uses urllib, so no extra dependency.
    """

    URL = "https://api.kavenegar.com/v1/{api_key}/sms/send.json"
    TIMEOUT_SECONDS = 10

    def send(self, phone, body):
        api_key = getattr(settings, "SMS_API_KEY", "")
        if not api_key:
            raise SmsSendError("SMS_API_KEY is not set.")

        data = urllib.parse.urlencode(
            {"receptor": phone, "message": body, "sender": getattr(settings, "SMS_SENDER", "")}
        ).encode()
        request = urllib.request.Request(self.URL.format(api_key=api_key), data=data, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.TIMEOUT_SECONDS) as response:
                payload = json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            # Kavenegar answers errors with a JSON body and a non-200 code.
            raise SmsSendError(f"Kavenegar HTTP {exc.code}: {exc.read()[:200]!r}") from exc
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            raise SmsSendError(f"Kavenegar unreachable: {exc}") from exc

        status = payload.get("return", {}).get("status")
        if status != 200:
            raise SmsSendError(f"Kavenegar refused: {payload.get('return')}")
        entries = payload.get("entries") or [{}]
        return str(entries[0].get("messageid", ""))


def get_backend() -> BaseSmsBackend:
    path = getattr(settings, "SMS_BACKEND", "apps.notifications.backends.ConsoleSmsBackend")
    return import_string(path)()
