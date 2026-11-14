import { type FormEvent, useState } from "react";
import type { Zone } from "./gateway";
import { errorMessage, formatFee } from "./presenter";
import { useFeeQuote } from "./useFeeQuote";

export function FeeScreen() {
  const [weight, setWeight] = useState("");
  const [zone, setZone] = useState<Zone>("local");
  const { result, quote } = useFeeQuote();

  function submit(event: FormEvent) {
    event.preventDefault();
    void quote(Number(weight), zone);
  }

  return (
    <main>
      <h1>Parcel fee</h1>
      <form id="fees-quote-form" onSubmit={submit}>
        <label htmlFor="fees-weight-input">Weight (g)</label>
        <input
          id="fees-weight-input"
          type="number"
          value={weight}
          onChange={(event) => setWeight(event.target.value)}
        />
        <label htmlFor="fees-zone-select">Zone</label>
        <select id="fees-zone-select" value={zone} onChange={(event) => setZone(event.target.value as Zone)}>
          <option value="local">Local</option>
          <option value="national">National</option>
          <option value="abroad">Abroad</option>
        </select>
        <button id="fees-quote-submit" type="submit" form="fees-quote-form">
          Quote
        </button>
      </form>
      {result?.status === "ok" && <p role="status">Fee: {formatFee(result.cents)}</p>}
      {result?.status === "error" && <p role="alert">{errorMessage(result.error)}</p>}
    </main>
  );
}
