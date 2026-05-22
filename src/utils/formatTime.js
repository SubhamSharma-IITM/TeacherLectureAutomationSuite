/**
 * formatTime.js
 * Utility to format seconds into MM:SS or HH:MM:SS strings.
 */

/**
 * Format a duration in seconds as MM:SS.
 * Hours overflow into minutes (e.g. 3661s → "61:01") — matches export.py behaviour.
 * @param {number} seconds
 * @returns {string}
 */
export function formatTime(seconds) {
  if (typeof seconds !== "number" || isNaN(seconds) || seconds < 0) return "00:00";
  const total = Math.floor(seconds);
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

/**
 * Format a duration in seconds as HH:MM:SS.
 * Useful for displaying long lecture durations.
 * @param {number} seconds
 * @returns {string}
 */
export function formatTimeLong(seconds) {
  if (typeof seconds !== "number" || isNaN(seconds) || seconds < 0) return "00:00:00";
  const total = Math.floor(seconds);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

/**
 * Format seconds as a human-readable string (e.g. "1h 4m 21s").
 * Good for showing total lecture duration.
 * @param {number} seconds
 * @returns {string}
 */
export function formatDuration(seconds) {
  if (typeof seconds !== "number" || isNaN(seconds) || seconds < 0) return "0s";
  const total = Math.floor(seconds);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  const parts = [];
  if (h > 0) parts.push(`${h}h`);
  if (m > 0) parts.push(`${m}m`);
  if (s > 0 || parts.length === 0) parts.push(`${s}s`);
  return parts.join(" ");
}
