/**
 * Stage 3.2 — the short alert sound for a new ticket. Synthesised with the
 * Web Audio API (two soft tones), so there is no audio file to ship.
 *
 * Browsers only allow sound after the user has interacted with the page;
 * unlockChime() is called on the first click/keypress, and before that
 * playChime() quietly does nothing. The operator can also mute it — a
 * per-browser preference in localStorage.
 */

const MUTE_KEY = "operator-sound-muted";

let context: AudioContext | null = null;

export function isChimeMuted(): boolean {
  try {
    return window.localStorage.getItem(MUTE_KEY) === "1";
  } catch {
    return false;
  }
}

export function setChimeMuted(muted: boolean): void {
  try {
    if (muted) window.localStorage.setItem(MUTE_KEY, "1");
    else window.localStorage.removeItem(MUTE_KEY);
  } catch {
    // Not persisted; fine.
  }
}

/** Call from a user gesture: creates/resumes the AudioContext the browser allows. */
export function unlockChime(): void {
  if (typeof window === "undefined" || !("AudioContext" in window)) return;
  try {
    context ??= new AudioContext();
    if (context.state === "suspended") void context.resume();
  } catch {
    context = null;
  }
}

export function playChime(): void {
  if (!context || context.state !== "running" || isChimeMuted()) return;
  const start = context.currentTime;
  // A rising two-note "ding-dong": 660 Hz then 880 Hz, each ~0.18s.
  [660, 880].forEach((frequency, i) => {
    const oscillator = context!.createOscillator();
    const gain = context!.createGain();
    const at = start + i * 0.18;
    oscillator.type = "sine";
    oscillator.frequency.setValueAtTime(frequency, at);
    gain.gain.setValueAtTime(0.0001, at);
    gain.gain.exponentialRampToValueAtTime(0.18, at + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, at + 0.17);
    oscillator.connect(gain).connect(context!.destination);
    oscillator.start(at);
    oscillator.stop(at + 0.18);
  });
}
