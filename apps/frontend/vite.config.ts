import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Local UI can call the GCP demo gateway without browser CORS by proxying /api.
const apiProxyTarget =
  process.env.VITE_DEV_API_PROXY_TARGET ?? "http://136.85.35.106:8080";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: apiProxyTarget,
        changeOrigin: true,
      },
    },
  },
});
