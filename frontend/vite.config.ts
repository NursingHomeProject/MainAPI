import path from "node:path"

import react from "@vitejs/plugin-react"
import { defineConfig, loadEnv } from "vite"
import { VitePWA } from "vite-plugin-pwa"

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "")
  const proxyTarget = env.VITE_PROXY_TARGET || "http://127.0.0.1:8000"

  return {
    plugins: [
      react(),
      VitePWA({
        registerType: "autoUpdate",
        manifest: {
          name: "Casa Assistencial",
          short_name: "Assistencial",
          description: "Painel administrativo para gestão de pacientes, medicamentos, estoque e alertas.",
          theme_color: "#16796a",
          background_color: "#f8faf8",
          display: "standalone",
          orientation: "any",
          scope: "/",
          start_url: "/dashboard",
          icons: [
            {
              src: "/pwa-icon.svg",
              sizes: "any",
              type: "image/svg+xml",
              purpose: "any",
            },
            {
              src: "/pwa-icon.svg",
              sizes: "any",
              type: "image/svg+xml",
              purpose: "maskable",
            },
          ],
        },
        workbox: {
          globPatterns: ["**/*.{js,css,html,svg,woff,woff2}"],
          navigateFallback: "/index.html",
          navigateFallbackDenylist: [/^\/api\//],
          runtimeCaching: [
            {
              urlPattern: /^\/api\/.*/i,
              handler: "NetworkFirst",
              options: {
                cacheName: "api-cache",
                expiration: {
                  maxEntries: 100,
                  maxAgeSeconds: 5 * 60,
                },
                networkTimeoutSeconds: 10,
              },
            },
          ],
        },
      }),
    ],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
    server: {
      host: "127.0.0.1",
      port: 5173,
      proxy: {
        "/api": {
          target: proxyTarget,
          changeOrigin: true,
          rewrite: (requestPath) => requestPath.replace(/^\/api/, ""),
        },
      },
    },
  }
})
