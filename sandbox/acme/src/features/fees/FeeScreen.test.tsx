import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { FeeScreen } from "./FeeScreen";
import { quoteFee } from "./gateway";
import { formatFee } from "./presenter";

vi.mock("./gateway", () => ({ quoteFee: vi.fn() }));

afterEach(() => {
  cleanup();
  vi.mocked(quoteFee).mockReset();
});

function quote(weight: string) {
  fireEvent.change(screen.getByLabelText("Weight (g)"), { target: { value: weight } });
  fireEvent.click(screen.getByRole("button", { name: "Quote" }));
}

test("it shows the fee the backend quotes", async () => {
  vi.mocked(quoteFee).mockResolvedValue({ status: "ok", cents: 1250 });
  render(<FeeScreen />);
  quote("2000");
  expect((await screen.findByRole("status")).textContent).toBe("Fee: 12.50");
  expect(quoteFee).toHaveBeenCalledWith(2000, "local");
});

test("it says why a parcel is refused", async () => {
  vi.mocked(quoteFee).mockResolvedValue({ status: "error", error: { code: "TOO_HEAVY" } });
  render(<FeeScreen />);
  quote("31000");
  expect((await screen.findByRole("alert")).textContent).toBe("This parcel is over 30 kg.");
});

test("it writes cents as a decimal amount", () => {
  expect(formatFee(1250)).toBe("12.50");
  expect(formatFee(405)).toBe("4.05");
});
