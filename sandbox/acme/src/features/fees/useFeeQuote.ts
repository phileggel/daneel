import { useState } from "react";
import { type FeeResult, quoteFee, type Zone } from "./gateway";

export function useFeeQuote() {
  const [result, setResult] = useState<FeeResult | null>(null);

  async function quote(weightGrams: number, zone: Zone) {
    setResult(await quoteFee(weightGrams, zone));
  }

  return { result, quote };
}
