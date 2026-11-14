import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { FeeScreen } from "./features/fees/FeeScreen";

createRoot(document.getElementById("root") as HTMLElement).render(
  <StrictMode>
    <FeeScreen />
  </StrictMode>,
);
