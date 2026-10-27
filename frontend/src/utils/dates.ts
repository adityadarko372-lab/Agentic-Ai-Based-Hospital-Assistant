/**
 * Date helpers. Appointment rules use the date in India (UTC+05:30), matching
 * the backend's `today_in_india()`, whatever timezone the laptop is set to.
 */

const IST_OFFSET_MS = 330 * 60 * 1000;
const DAY_MS = 24 * 60 * 60 * 1000;

/** Today's date in India as YYYY-MM-DD. */
export function todayInIndia(now: number = Date.now()): string {
  return new Date(now + IST_OFFSET_MS).toISOString().slice(0, 10);
}

/** Adds whole days to a YYYY-MM-DD string. */
export function addDays(isoDate: string, days: number): string {
  const [year, month, day] = isoDate.split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, day) + days * DAY_MS).toISOString().slice(0, 10);
}

/** "2026-11-02" → "2 Nov 2026" (parsed as a calendar date, not a moment in time). */
export function formatCalendarDate(isoDate: string): string {
  const [year, month, day] = isoDate.split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, day)).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
}

/** Timestamp → "26 Oct 2026, 10:42 pm" in the viewer's local time. */
export function formatTimestamp(isoDateTime: string): string {
  return new Date(isoDateTime).toLocaleString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

/** Timestamp → "just now", "5 min ago", "3 h ago" or a date for older events. */
export function formatRelative(isoDateTime: string, now: number = Date.now()): string {
  const seconds = Math.round((now - new Date(isoDateTime).getTime()) / 1000);
  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} h ago`;
  return formatTimestamp(isoDateTime);
}
