import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * Merge Tailwind and conditional class names.
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Format a date into a readable, localized string.
 */
export function formatDate(
  value: string | number | Date,
  options?: Intl.DateTimeFormatOptions
) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';

  const defaultOptions: Intl.DateTimeFormatOptions = {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  };

  return date.toLocaleDateString(undefined, { ...defaultOptions, ...options });
}

/**
 * Human-friendly "time ago" strings without pulling in date-fns.
 */
export function formatDistanceToNow(value: string | number | Date) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';

  let delta = (date.getTime() - Date.now()) / 1000;
  const formatter = new Intl.RelativeTimeFormat('en', { numeric: 'auto' });

  const divisions = [
    { amount: 60, unit: 'second' as const },
    { amount: 60, unit: 'minute' as const },
    { amount: 24, unit: 'hour' as const },
    { amount: 7, unit: 'day' as const },
    { amount: 4.34524, unit: 'week' as const },
    { amount: 12, unit: 'month' as const },
    { amount: Number.POSITIVE_INFINITY, unit: 'year' as const },
  ];

  for (const division of divisions) {
    if (Math.abs(delta) < division.amount) {
      return formatter.format(Math.round(delta), division.unit);
    }
    delta /= division.amount;
  }

  return '';
}

/**
 * Format large numbers using K / M / B suffixes.
 */
export function formatNumber(value: number, decimals = 1) {
  const abs = Math.abs(value);
  if (abs >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(decimals)}B`;
  if (abs >= 1_000_000) return `${(value / 1_000_000).toFixed(decimals)}M`;
  if (abs >= 1_000) return `${(value / 1_000).toFixed(decimals)}K`;
  return value.toString();
}

/**
 * Calculate a percentage with safe zero handling.
 */
export function calculatePercentage(value: number, total: number, decimals = 1) {
  if (!Number.isFinite(value) || !Number.isFinite(total) || total === 0) return 0;
  return parseFloat(((value / total) * 100).toFixed(decimals));
}
