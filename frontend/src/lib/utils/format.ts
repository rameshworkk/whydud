/** Formatting utilities for prices, scores, dates. */

/** Convert paisa (integer) to ₹ display string. e.g. 199900 → "₹1,999" */
export function formatPrice(paisa: number | null | undefined): string {
  if (paisa == null) return "—";
  const rupees = paisa / 100;
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(rupees);
}

/** Format a DudScore number to display. e.g. 82.5 → "82" */
export function formatDudScore(score: number | null): string {
  if (score == null) return "—";
  return Math.round(score).toString();
}

/** Return Tailwind colour class for a DudScore. */
export function dudScoreColour(score: number | null): string {
  if (score == null) return "text-score-unrated";
  if (score >= 90) return "text-score-excellent";
  if (score >= 70) return "text-score-good";
  if (score >= 50) return "text-score-average";
  if (score >= 30) return "text-score-below";
  return "text-score-dud";
}

/** Format ISO timestamp to local date string. */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Intl.DateTimeFormat("en-IN", { dateStyle: "medium" }).format(new Date(iso));
}

/** Format ISO timestamp to relative time. e.g. "3 hours ago" */
export function formatRelative(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const seconds = Math.round(diff / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  return `${days}d ago`;
}

/** Clamp a number between min and max. */
export function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

/** Alias for formatRelative — "3h ago", "just now", etc. */
export const timeAgo = formatRelative;

/** Truncate a string to maxLen characters, appending "…" if cut. */
export function truncate(text: string, maxLen: number): string {
  if (text.length <= maxLen) return text;
  return text.slice(0, maxLen - 1) + "…";
}
