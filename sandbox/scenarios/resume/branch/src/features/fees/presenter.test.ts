import { expect, test } from "vitest";
import { errorMessage } from "./presenter";

test("each error code has its message", () => {
  expect(errorMessage({ code: "TOO_HEAVY" })).toBe("This parcel is over 30 kg.");
  expect(errorMessage({ code: "EMPTY_PARCEL" })).toBe("Enter a weight above zero.");
});
