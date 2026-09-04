import "@fontsource/archivo/latin-400.css";
import "@fontsource/archivo/latin-500.css";
import "@fontsource/archivo/latin-600.css";
import "@fontsource/archivo/latin-700.css";
import "@fontsource/azeret-mono/latin-400.css";
import "@fontsource/azeret-mono/latin-600.css";
import "@fontsource/source-serif-4/latin-600.css";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App";
import "./styles/global.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
