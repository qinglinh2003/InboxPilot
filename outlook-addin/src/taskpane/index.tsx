import React from "react";
import { createRoot } from "react-dom/client";
import { FluentProvider, webLightTheme } from "@fluentui/react-components";
import { App } from "./App";

/* global Office */
declare const Office: any;

function renderApp() {
  const container = document.getElementById("app");
  if (!container) {
    document.body.innerHTML = "<p style='padding:16px;color:red'>Root element #app not found</p>";
    return;
  }

  const root = createRoot(container);
  root.render(
    <React.StrictMode>
      <FluentProvider theme={webLightTheme}>
        <App />
      </FluentProvider>
    </React.StrictMode>,
  );
}

// Show loading indicator immediately
const loadingEl = document.getElementById("loading");

try {
  if (typeof Office !== "undefined" && Office.onReady) {
    Office.onReady((_info: any) => {
      if (loadingEl) loadingEl.style.display = "none";
      renderApp();
    });
  } else {
    // Office.js not loaded — render anyway for testing
    if (loadingEl) loadingEl.style.display = "none";
    renderApp();
  }
} catch (err) {
  document.body.innerHTML = `<p style="padding:16px;color:red">Init error: ${err}</p>`;
}

// Timeout fallback: if Office.onReady hasn't fired in 10s, render anyway
setTimeout(() => {
  const container = document.getElementById("app");
  if (container && container.children.length === 0) {
    if (loadingEl) loadingEl.style.display = "none";
    console.warn("Office.onReady timeout — rendering without Office context");
    renderApp();
  }
}, 10000);
