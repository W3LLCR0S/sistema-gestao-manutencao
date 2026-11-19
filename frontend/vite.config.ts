import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// O proxy de /api faz navegador e API serem a "mesma origem" (cookie SameSite=Lax + CSRF sem CORS).
// Isso vale tambem para o celular na rede local: ele fala so com a porta 5173 (ver docs/ACESSO_PELO_CELULAR.md).
const destinoApi = process.env.VITE_API_DESTINO ?? "http://127.0.0.1:8000";
// changeOrigin:false mantem o Host do navegador; a API compara Origin com Host e recusaria o login (403).
const proxyApi = { "/api": { target: destinoApi, changeOrigin: false } };

export default defineConfig({
  plugins: [react()],
  server: { host: true, port: 5173, strictPort: true, proxy: proxyApi },
  preview: { host: true, port: 5173, proxy: proxyApi },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/testes/preparar.ts"],
    css: false,
  },
});
