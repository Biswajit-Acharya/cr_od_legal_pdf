import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const backendUrl = process.env.VITE_BACKEND_URL || 'http://127.0.0.1:8002'
  return {
    plugins: [
      react(),
      tailwindcss(),
    ],
    css: {
      postcss: false
    },
    optimizeDeps: {
      include: ['uuid', 'pdf-lib', 'perfect-freehand', 'react-pdf']
    },
    server: {
      proxy: {
        '/api': backendUrl,
        '/document-management': backendUrl,
        '/pdf': backendUrl,
        '/convert-to-pdf': backendUrl,
        '/convert-from-pdf': backendUrl,
        '/pdf-copyright-protection': backendUrl,
        '/organize_pdf_services': backendUrl,
        '/v1': backendUrl,
      }
    }
  }
})
