/** @type {import('tailwindcss').Config} */
// Design tokens — PLAN_SONNET.md sectiunea 4. Nu se folosesc valori in afara acestor tokeni.
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class', // dark este singurul mode; clasa `dark` e mereu pe <html>
  theme: {
    extend: {
      colors: {
        // Albastru FEG — structura (culoarea "casei", ~60%)
        navy: {
          950: '#070B1A',
          900: '#0B1229',
          800: '#101B3D',
          700: '#16264F',
          600: '#1D3468',
        },
        feg: {
          DEFAULT: '#1E5BFF',
          600: '#1747D6',
          400: '#4E82FF',
          200: '#A9C2FF',
        },
        // Galben Fortuna — accentul (~30%)
        fortuna: {
          DEFAULT: '#FFC800',
          600: '#E0AC00',
          400: '#FFD84D',
          200: '#FFEEA8',
        },
        // Rosu casa de pariuri — urgenta (~10%)
        bet: {
          DEFAULT: '#F03A2E',
          600: '#C92B21',
          400: '#FF6A5E',
          200: '#FFC1BB',
        },
        // Neutrale calde peste albastru
        paper: {
          DEFAULT: '#FBF7EE',
          200: '#F2ECDE',
        },
        ink: '#0A0E1C',
      },
      fontFamily: {
        display: ["'Bricolage Grotesque'", "'Arial Black'", 'sans-serif'],
        sans: ["'Inter'", 'system-ui', 'sans-serif'],
        mono: ["'JetBrains Mono'", 'ui-monospace', 'monospace'],
      },
      spacing: {
        13: '3.25rem', // inaltimea butonului `lg` (h-13), singura exceptie ceruta de plan
      },
      maxHeight: {
        modal: '85dvh', // inaltimea maxima a modalului pe desktop
      },
      borderRadius: {
        xl: '12px', // butoane, input-uri
        '2xl': '16px', // carduri
      },
      boxShadow: {
        card: '0 2px 24px rgba(0,0,0,.35)',
        glow: '0 0 28px rgba(255,200,0,.25)', // doar pe CTA-ul principal
      },
      transitionTimingFunction: {
        DEFAULT: 'cubic-bezier(.2,.8,.2,1)',
        smooth: 'cubic-bezier(.2,.8,.2,1)',
      },
      transitionDuration: {
        150: '150ms', // hover / press
        220: '220ms', // intrare element
        400: '400ms', // stampila
      },
      zIndex: {
        navbar: '10',
        betslip: '20',
        toast: '30',
        modal: '40',
      },
      keyframes: {
        'stamp-in': {
          '0%': { transform: 'rotate(-12deg) scale(1.4)', opacity: '0' },
          '55%': { opacity: '1' },
          '100%': { transform: 'rotate(-12deg) scale(1)', opacity: '1' },
        },
        'pulse-urgent': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.5' },
        },
        shimmer: {
          '100%': { transform: 'translateX(100%)' },
        },
        'count-pop': {
          '0%': { transform: 'scale(1)' },
          '45%': { transform: 'scale(1.14)' },
          '100%': { transform: 'scale(1)' },
        },
      },
      animation: {
        'stamp-in': 'stamp-in 400ms cubic-bezier(.2,.8,.2,1) both',
        'pulse-urgent': 'pulse-urgent 1s ease-in-out infinite',
        shimmer: 'shimmer 1.6s ease-in-out infinite',
        'count-pop': 'count-pop 220ms cubic-bezier(.2,.8,.2,1)',
      },
    },
  },
  plugins: [],
}
