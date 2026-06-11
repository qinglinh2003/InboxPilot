import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(async () => {
  // Dev HTTPS certs — only needed for `vite dev` / `vite preview`.
  // Skipped during production builds (Docker/CI) where certs are unavailable.
  let httpsOptions: Record<string, unknown> | false = false;
  if (process.env.NODE_ENV !== "production") {
    try {
      const devCerts = await import("office-addin-dev-certs");
      httpsOptions =
        (await devCerts.getHttpsServerOptions()) as Record<string, unknown>;
    } catch {
      // Certs unavailable — HTTPS disabled for dev server
    }
  }

  return {
    plugins: [react()],
    base: "/",
    root: "src/taskpane",
    build: {
      outDir: "../../dist",
      emptyOutDir: true,
    },
    server: {
      port: 3000,
      https: httpsOptions || undefined,
    },
    preview: {
      port: 3000,
      https: httpsOptions || undefined,
    },
  };
});
