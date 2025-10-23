import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Returns a formatted accuracy percentage string or '-' when null/undefined.
// Shows 0.0% when accuracy is 0.
export function formatAccuracy(accuracy: number | null | undefined, fractionDigits: number = 1): string {
  if (accuracy === null || accuracy === undefined) return '-';
  const percentage = accuracy * 100;
  return `${percentage.toFixed(fractionDigits)}%`;
}
