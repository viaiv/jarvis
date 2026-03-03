import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const backendPort = process.env.JARVIS_PORT || '8000'
const backendUrl = `http://localhost:${backendPort}`

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/ws': { target: backendUrl, ws: true },
      '/chat': { target: backendUrl },
      '/auth': { target: backendUrl },
      '/admin': { target: backendUrl },
    },
  },
})
