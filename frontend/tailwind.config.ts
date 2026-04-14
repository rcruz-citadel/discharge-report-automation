import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        navy: {
          DEFAULT: '#132e45',
          light: '#1b4459',
          dark: '#0e2233',
        },
        orange: {
          DEFAULT: '#e07b2a',
          hover: '#c96920',
        },
        page: '#f0f2f5',
        surface: '#ffffff',
        'text-primary': '#132e45',
        'text-secondary': '#556e81',
        'text-muted': '#7e96a6',
        'text-light': '#a8c4d8',
        border: '#d0dae3',
        'border-light': '#e8ecf0',
        status: {
          none: '#cbd5e0',
          'none-bg': '#edf2f7',
          'none-text': '#718096',
          made: '#e07b2a',
          'made-bg': '#fef3e2',
          'made-text': '#c05621',
          complete: '#38a169',
          'complete-bg': '#e6ffed',
          'complete-text': '#22753a',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
      },
      borderRadius: {
        sm: '6px',
        md: '8px',
        lg: '10px',
        xl: '12px',
        '2xl': '14px',
        '3xl': '16px',
        full: '9999px',
      },
      boxShadow: {
        chip: '0 2px 6px rgba(19,46,69,0.06)',
        card: '0 2px 8px rgba(19,46,69,0.07)',
        panel: '0 4px 18px rgba(19,46,69,0.10)',
        header: '0 4px 18px rgba(19,46,69,0.18)',
        login: '0 6px 28px rgba(19,46,69,0.22)',
        'btn-cta': '0 2px 8px rgba(224,123,42,0.35)',
        'input-focus': '0 0 0 2px rgba(19,46,69,0.15)',
      },
      transitionDuration: {
        fast: '120ms',
        base: '180ms',
        slow: '220ms',
      },
      transitionTimingFunction: {
        'panel-in': 'cubic-bezier(0.25, 0.46, 0.45, 0.94)',
        'panel-out': 'ease-in',
        button: 'ease',
      },
    },
  },
  plugins: [],
} satisfies Config
