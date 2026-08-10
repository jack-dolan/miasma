import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: true, // Listen on all addresses (0.0.0.0)
    port: 3000,
    strictPort: true,
    watch: {
      usePolling: true, // Needed for Docker on some systems
    },
    hmr: {
      port: 3000,
    },
  },
  preview: {
    host: true,
    port: 3000,
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    rollupOptions: {
      output: {
        // Function form, not the object form. Vite 8 builds with rolldown,
        // which accepts only a function here and fails the build outright with
        // "TypeError: manualChunks is not a function". Rollup accepts both, so
        // this form is correct before and after that upgrade.
        //
        // Order is load-bearing: the tests run longest-prefix first, because
        // `node_modules/react-router-dom/` and `node_modules/react-dom/` both
        // contain the string `react`, and a bare `react` test would swallow
        // them into vendor and silently collapse three chunks into one.
        manualChunks(id) {
          if (!id.includes('node_modules')) return
          if (/[\\/]node_modules[\\/]react-router-dom[\\/]/.test(id)) return 'router'
          if (/[\\/]node_modules[\\/]@tanstack[\\/]react-query[\\/]/.test(id)) return 'query'
          if (/[\\/]node_modules[\\/]react-dom[\\/]/.test(id)) return 'vendor'
          if (/[\\/]node_modules[\\/]react[\\/]/.test(id)) return 'vendor'
        },
      },
    },
  },
  define: {
    // Define global constants
    __APP_VERSION__: JSON.stringify(process.env.npm_package_version || '0.1.0'),
  },
  css: {
    devSourcemap: true,
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.js',
    css: true,
  },
})