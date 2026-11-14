import type { FeeError } from "./gateway";

/** 1250 -> "12.50" */
export function formatFee(cents: number): string {
  return `${Math.floor(cents / 100)}.${String(cents % 100).padStart(2, "0")}`;
}

export function errorMessage(error: FeeError): string {
  return error.code === "TOO_HEAVY" ? "This parcel is over 30 kg." : "Enter a weight above zero.";
}
