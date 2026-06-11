import React from "react";
import { createRoot } from "react-dom/client";
import { FluentProvider, webLightTheme } from "@fluentui/react-components";
import { App } from "./App";

/* global Office */
declare const Office: any;

Office.onReady((_info: any) => {
  const container = document.getElementById("app");
  if (!container) throw new Error("Root element #app not found");

  const root = createRoot(container);
  root.render(
    <React.StrictMode>
      <FluentProvider theme={webLightTheme}>
        <App />
      </FluentProvider>
    </React.StrictMode>,
  );
});
