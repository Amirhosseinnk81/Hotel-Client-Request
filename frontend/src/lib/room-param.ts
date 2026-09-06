/**
 * Parser for the room QR deep link: `/guest/login?room=305`.
 *
 * The value only ever PREFILLS the login form's room field — it is never
 * a lock and never an authentication shortcut. Login still validates the
 * national ID against that room and requires the room to be OCCUPIED, so
 * a tampered or mis-scanned code just fails to log in.
 *
 * Lives here rather than in the page so it can be unit-tested: the QR
 * codes get printed and stuck on hotel-room doors, and a parsing bug
 * would only surface as a guest standing in a corridor with a form that
 * won't fill.
 */

const PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹";
const ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩";

/** A room number is short and alphanumeric — "305", "12B", "A-4". */
const ROOM_PATTERN = /^[A-Za-z0-9-]{1,10}$/;

/**
 * Returns a clean room number, or "" for anything missing or malformed.
 *
 * Persian and Arabic-Indic digits are folded to ASCII: a QR generated
 * from a Persian-language room list can carry them, and the API only
 * accepts ASCII. Anything that doesn't look like a room number is
 * discarded rather than dropped into the field as-is, so a mangled link
 * leaves an empty input instead of junk the guest has to clear first.
 */
export function normalizeRoomParam(raw: string | null | undefined): string {
  if (!raw) return "";

  const ascii = raw
    .replace(/[۰-۹]/g, (d) => String(PERSIAN_DIGITS.indexOf(d)))
    .replace(/[٠-٩]/g, (d) => String(ARABIC_DIGITS.indexOf(d)))
    .trim();

  return ROOM_PATTERN.test(ascii) ? ascii : "";
}
