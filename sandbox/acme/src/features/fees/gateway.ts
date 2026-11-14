import { invoke } from "@tauri-apps/api/core";

export type Zone = "local" | "national" | "abroad";

export type FeeError = { code: "EMPTY_PARCEL" | "TOO_HEAVY" };

export type FeeResult = { status: "ok"; cents: number } | { status: "error"; error: FeeError };

/** The only place this feature talks to the backend. It returns the result, never throws. */
export async function quoteFee(weightGrams: number, zone: Zone): Promise<FeeResult> {
  try {
    const cents = await invoke<number>("quote_fee", { weightGrams, zone });
    return { status: "ok", cents };
  } catch (error) {
    return { status: "error", error: error as FeeError };
  }
}
