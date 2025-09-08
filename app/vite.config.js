import { defineConfig } from 'vite';
import legacy from '@vitejs/plugin-legacy';
import { resolve } from 'path';

export default defineConfig({
  plugins: [
    legacy({
      targets: ['defaults', 'not IE 11']
    })
  ],
  
  // Entry points for different pages
  build: {
    outDir: 'src/static/dist',
    emptyOutDir: true,
    manifest: true,
    ssr: false,
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'src/js/main.js'),
        dashboard: resolve(__dirname, 'src/js/dashboard.js'),
        'theme-switcher': resolve(__dirname, 'src/js/theme-switcher.js'),
        styles: resolve(__dirname, 'src/static/css/input.css')
      },
      external: [],
      output: {
        entryFileNames: 'js/[name]-[hash].js',
        chunkFileNames: 'js/[name]-[hash].js',
        assetFileNames: (assetInfo) => {
          if (assetInfo.name.endsWith('.css')) {
            return 'css/[name]-[hash][extname]';
          }
          if (assetInfo.name.match(/\.(woff|woff2|eot|ttf|otf)$/)) {
            return 'fonts/[name]-[hash][extname]';
          }
          return 'assets/[name]-[hash][extname]';
        }
      }
    }
  },
  
  // CSS preprocessing
  css: {
    postcss: {
      plugins: [
        require('tailwindcss'),
        require('autoprefixer')
      ]
    }
  },
  
  // Development server
  server: {
    port: 3001,
    cors: true,
    proxy: {
      // Proxy API calls to FastAPI during development
      '/api': 'http://localhost:8000'
    }
  },
  
  // Static asset handling
  assetsInclude: ['**/*.woff', '**/*.woff2', '**/*.eot', '**/*.ttf', '**/*.otf']
});