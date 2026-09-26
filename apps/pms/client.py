"""
Asking the PMS what changed (the pull half of Stage 3.3).

The hotel uses Harris (شرکت هریس). Harris publishes no public API
documentation — their web services are given to integration partners — so
what the hotel has to obtain from Harris support is:

  1. the endpoint that lists check-ins / check-outs / room changes since a
     given moment,
  2. a credential for it (they usually issue a token or user+password),
  3. one real sample response per event.

Everything else is already here: HarrisPmsClient sends the request and hands
the raw items to services.apply_event(), which maps their field names
through settings.PMS_FIELD_MAP. Adapting to the real API should be a
settings change; if their shape turns out to be unusual, override
`fetch_events` in a subclass and point PMS_CLIENT at it.

Until then PMS_CLIENT defaults to FilePmsClient, which reads events from a
JSON file — enough to build, test and demo the whole flow.
"""

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from django.conf import settings
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)


class PmsUnavailable(Exception):
    """The PMS couldn't be reached or answered with something unusable."""


class BasePmsClient:
    def fetch_events(self, since=None):
        """Return a list of raw PMS event dicts, oldest first."""
        raise NotImplementedError


class FilePmsClient(BasePmsClient):
    """
    Reads events from the JSON file at settings.PMS_EVENTS_FILE (a list, or
    an object with an "events" list). The default client: it lets the whole
    pull path run — and be tested — before Harris hands over API access.
    """

    def fetch_events(self, since=None):
        path = getattr(settings, "PMS_EVENTS_FILE", "")
        if not path:
            return []
        file = Path(path)
        if not file.exists():
            raise PmsUnavailable(f"PMS_EVENTS_FILE not found: {path}")
        try:
            payload = json.loads(file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise PmsUnavailable(f"PMS_EVENTS_FILE is not valid JSON: {exc}") from exc
        return payload.get("events", []) if isinstance(payload, dict) else payload


class HarrisPmsClient(BasePmsClient):
    """
    Harris over HTTP. Built from settings so the hotel can point it at their
    own installation without touching code:

      PMS_BASE_URL     e.g. https://harris.hotel.local/api
      PMS_EVENTS_PATH  the "what changed since" path (default /events)
      PMS_API_KEY      sent as PMS_AUTH_HEADER (default "Authorization:
                       Bearer {key}")
      PMS_SINCE_PARAM  query parameter for the cursor (default "since")
      PMS_ITEMS_PATH   dotted path to the list inside their response
                       (default "" = the response is the list)

    urllib, so no new dependency.
    """

    TIMEOUT_SECONDS = 20

    def fetch_events(self, since=None):
        base = getattr(settings, "PMS_BASE_URL", "")
        if not base:
            raise PmsUnavailable("PMS_BASE_URL is not set.")

        path = getattr(settings, "PMS_EVENTS_PATH", "/events")
        query = {}
        if since is not None:
            query[getattr(settings, "PMS_SINCE_PARAM", "since")] = since.isoformat()
        url = f"{base.rstrip('/')}{path}"
        if query:
            url = f"{url}?{urllib.parse.urlencode(query)}"

        header_template = getattr(settings, "PMS_AUTH_HEADER", "Authorization: Bearer {key}")
        name, _, value = header_template.partition(":")
        request = urllib.request.Request(
            url, headers={name.strip(): value.strip().format(key=getattr(settings, "PMS_API_KEY", ""))}
        )
        try:
            with urllib.request.urlopen(request, timeout=self.TIMEOUT_SECONDS) as response:
                body = json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            raise PmsUnavailable(f"Harris answered HTTP {exc.code}: {exc.read()[:200]!r}") from exc
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            raise PmsUnavailable(f"Harris is unreachable: {exc}") from exc

        items_path = getattr(settings, "PMS_ITEMS_PATH", "")
        for part in filter(None, items_path.split(".")):
            body = (body or {}).get(part) if isinstance(body, dict) else None
        if not isinstance(body, list):
            raise PmsUnavailable("The PMS response did not contain a list of events (see PMS_ITEMS_PATH).")
        return body


def get_client() -> BasePmsClient:
    path = getattr(settings, "PMS_CLIENT", "apps.pms.client.FilePmsClient")
    return import_string(path)()
