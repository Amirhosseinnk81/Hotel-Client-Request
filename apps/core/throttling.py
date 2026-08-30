from rest_framework.throttling import AnonRateThrottle


class GuestLoginRateThrottle(AnonRateThrottle):
    """
    Throttles guest login attempts by client IP.

    Guest authentication has no password (national_id + room_number
    only), so without a dedicated limit here, an attacker could brute
    force room/national-ID combinations with unlimited attempts. Scoped
    separately from the default 'anon' rate so it can be tuned
    independently via DEFAULT_THROTTLE_RATES['guest_login'].
    """

    scope = "guest_login"