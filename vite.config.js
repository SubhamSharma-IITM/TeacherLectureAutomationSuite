import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],

  resolve: {
    alias: {
      // FIX: allow "@/components/..." style imports in addition to relative paths
      "@": path.resolve(__dirname, "./src"),
    },
  },

  server: {
    port: 5173,
    // FIX: proxy API calls to FastAPI in dev — avoids CORS issues locally
    proxy: {
      "/api": {
        target: process.env.VITE_API_URL || "http://localhost:8000",
        changeOrigin: true,
        // Uncomment if your FastAPI is behind a self-signed cert in dev:
        // secure: false,
      },
    },
  },

  build: {
    outDir: "dist",
    // FIX: warn when any chunk exceeds 600KB (default 500KB is too tight for Noto fonts)
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        // FIX: split vendor code into a separate chunk for better caching
        manualChunks: {
          vendor: ["react", "react-dom", "react-router-dom"],
          axios:  ["axios"],
        },
      },
    },
  },

  // FIX: expose env vars with VITE_ prefix to the browser bundle
  envPrefix: "VITE_",
});
