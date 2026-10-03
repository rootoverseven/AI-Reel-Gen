import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const BACKEND = 'http://127.0.0.1:8000'

// https://vitejs.dev/config/
// NOTE: do not proxy the bare assets prefix - the Vite build emits its own bundle there.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/generate-script': BACKEND,
      '/generate-video': BACKEND,
      '/voices': BACKEND,
      '/library': BACKEND,
      '/assets/backgrounds': BACKEND,
      '/assets/characters': BACKEND,
      '/output': BACKEND,
    }
  }
})
