const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/**
 * The UTC date of an ISO time as /shopping shows the date of its prices, e.g.
 * "13 Oct 2026" (DEC-1102); null when it does not parse.
 */
export function formatPricesDate(iso: string | undefined): string | null {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  return `${date.getUTCDate()} ${MONTHS[date.getUTCMonth()]} ${date.getUTCFullYear()}`;
}

/** The clock time of a moment in the browser's time zone, as /shopping's stop line shows it: "22:41:05". */
export function clockTime(at: number): string {
  return new Date(at).toLocaleTimeString('en-GB', { hour12: false });
}
