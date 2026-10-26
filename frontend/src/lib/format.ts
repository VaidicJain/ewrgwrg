/** Display helpers. Everything is UTC so server and browser always render the same text. */

export function formatNumber(value: number, digits = 0): string {
  return new Intl.NumberFormat("en-GB", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value);
}

export function formatMw(value: number, digits = 0): string {
  return `${formatNumber(value, digits)} MW`;
}

/** Always shows the sign so over- and under-forecasts are obvious: +1,852 MW / -86 MW. */
export function formatSignedMw(value: number, digits = 0): string {
  const rounded = Number(value.toFixed(digits));
  const sign = rounded > 0 ? "+" : rounded < 0 ? "-" : "";
  return `${sign}${formatNumber(Math.abs(rounded), digits)} MW`;
}

export function formatPercent(value: number, digits = 1): string {
  return `${formatNumber(value, digits)}%`;
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

function parseUtc(value: string): Date {
  // Accept both "2026-01-02" and "2026-01-02T07:30:00Z".
  return new Date(value.length === 10 ? `${value}T00:00:00Z` : value);
}

/** "2 Jan" */
export function formatShortDay(value: string): string {
  const date = parseUtc(value);
  return `${date.getUTCDate()} ${MONTHS[date.getUTCMonth()]}`;
}

/** "Fri 2 Jan" */
export function formatDay(value: string): string {
  const date = parseUtc(value);
  return `${WEEKDAYS[date.getUTCDay()]} ${formatShortDay(value)}`;
}

/** "07:30" taken straight from an ISO timestamp. */
export function formatTime(iso: string): string {
  return iso.slice(11, 16);
}

/** "Thu 1 Jan, 07:30" */
export function formatDayTime(iso: string): string {
  return `${formatDay(iso)}, ${formatTime(iso)}`;
}

/** Axis labels: dates for long ranges, clock times for short ones. */
export function formatAxisTick(iso: string, spanDays: number): string {
  return spanDays > 3 ? formatShortDay(iso) : `${formatShortDay(iso)} ${formatTime(iso)}`;
}

/** Whole days covered by an inclusive start/end date pair. */
export function spanInDays(startDate: string, endDate: string): number {
  const ms = parseUtc(endDate).getTime() - parseUtc(startDate).getTime();
  return Math.round(ms / 86_400_000) + 1;
}
