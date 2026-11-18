import React from "react";
import ReactDOM from "react-dom/client";
import { ThemeProvider } from "@avrig/ui";
import App from "./App";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <ThemeProvider defaultTheme="system" storageKey="avrig-desktop-theme">
      <App />
    </ThemeProvider>
  </React.StrictMode>
);
