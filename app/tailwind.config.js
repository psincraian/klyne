/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/templates/**/*.html",
    "./src/static/**/*.js",
  ],
  theme: {
    extend: {
      fontFamily: {
        'sans': ['Inter', 'system-ui', 'sans-serif'],
      },
      colors: {
        'klyne': {
          50: '#e0e7ff',
          100: '#c7d2fe', 
          500: '#6366f1',
          600: '#5b21b6',
          700: '#4c1d95',
          800: '#3730a3',
          900: '#312e81',
        }
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(20px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
      }
    },
  },
  plugins: [
    require('daisyui'),
    require('@tailwindcss/typography'),
  ],
  daisyui: {
    themes: [
      {
        klyne: {
          "primary": "#6366f1",
          "primary-content": "#ffffff",
          "secondary": "#8b5cf6", 
          "secondary-content": "#ffffff",
          "accent": "#10b981",
          "accent-content": "#ffffff",
          "neutral": "#374151",
          "neutral-content": "#ffffff",
          "base-100": "#ffffff",
          "base-200": "#f9fafb",
          "base-300": "#f3f4f6",
          "base-content": "#1f2937",
          "info": "#3b82f6",
          "info-content": "#ffffff",
          "success": "#10b981",
          "success-content": "#ffffff",
          "warning": "#f59e0b", 
          "warning-content": "#ffffff",
          "error": "#ef4444",
          "error-content": "#ffffff",
        },
        "klyne-dark": {
          "primary": "#6366f1",
          "primary-content": "#ffffff",
          "secondary": "#8b5cf6", 
          "secondary-content": "#ffffff",
          "accent": "#10b981",
          "accent-content": "#ffffff",
          "neutral": "#64748b",
          "neutral-content": "#f1f5f9",
          "base-100": "#0f172a",
          "base-200": "#1e293b",
          "base-300": "#334155",
          "base-content": "#f1f5f9",
          "info": "#3b82f6",
          "info-content": "#ffffff",
          "success": "#10b981",
          "success-content": "#ffffff",
          "warning": "#f59e0b", 
          "warning-content": "#ffffff",
          "error": "#ef4444",
          "error-content": "#ffffff",
        },
      },
      "dark",
    ],
    darkTheme: "dark",
    base: true,
    styled: true,
    utils: true,
    prefix: "",
    logs: true,
    themeRoot: ":root",
  },
}