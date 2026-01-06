const defaultTheme = require('tailwindcss/defaultTheme');

/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './new-components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Open Sans"', ...defaultTheme.fontFamily.sans],
        heading: ['"Poppins"', ...defaultTheme.fontFamily.sans],
        body: ['"Open Sans"', ...defaultTheme.fontFamily.sans],
      },
      colors: {
        theme: {
          primary: '#2563EB',
          secondary: '#3B82F6',
          cta: '#F97316',
          light: '#F8FAFC',
          dark: '#151622',
          'dark-container': '#232734',
          success: '#52C41A',
          error: '#FF4D4F',
          warning: '#FAAD14',
          text: '#1E293B',
          border: '#E2E8F0',
        },
        // SaaS 专业配色扩展
        primary: {
          50: '#EFF6FF',
          100: '#DBEAFE',
          200: '#BFDBFE',
          300: '#93C5FD',
          400: '#60A5FA',
          500: '#3B82F6',
          600: '#2563EB',
          700: '#1D4ED8',
          800: '#1E40AF',
          900: '#1E3A8A',
        },
        gradientL: '#00DAEF',
        gradientR: '#105EFF',
      },
      boxShadow: {
        'glass-sm': '0 2px 8px rgba(37, 99, 235, 0.08)',
        'glass-md': '0 4px 16px rgba(37, 99, 235, 0.12)',
        'glass-lg': '0 8px 24px rgba(37, 99, 235, 0.15)',
        'glass-xl': '0 12px 32px rgba(37, 99, 235, 0.18)',
        'card-hover': '0 20px 40px rgba(37, 99, 235, 0.15)',
      },
      transitionDuration: {
        '400': '400ms',
      },
      transitionTimingFunction: {
        'smooth': 'cubic-bezier(0.4, 0, 0.2, 1)',
        'glass': 'cubic-bezier(0.25, 0.46, 0.45, 0.94)',
      },
      backgroundColor: {
        bar: '#e0e7f2',
      },
      textColor: {
        default: '#0C75FC',
      },
      backgroundImage: {
        'gradient-light': "url('/images/bg.png')",
        'gradient-dark': 'url("/images/bg_dark.png")',
        'button-gradient': 'linear-gradient(to right, theme("colors.gradientL"), theme("colors.gradientR"))',
      },
      keyframes: {
        pulse1: {
          '0%, 100%': { transform: 'scale(1)', backgroundColor: '#bdc0c4' },
          '33.333%': { transform: 'scale(1.5)', backgroundColor: '#525964' },
        },
        pulse2: {
          '0%, 100%': { transform: 'scale(1)', backgroundColor: '#bdc0c4' },
          '33.333%': { transform: 'scale(1.0)', backgroundColor: '#bdc0c4' },
          '66.666%': { transform: 'scale(1.5)', backgroundColor: '#525964' },
        },
        pulse3: {
          '0%, 66.666%': { transform: 'scale(1)', backgroundColor: '##bdc0c4' },
          '100%': { transform: 'scale(1.5)', backgroundColor: '#525964' },
        },
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideIn: {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(0)' },
        },
        glass: {
          '0%, 100%': { backdropFilter: 'blur(10px)', backgroundColor: 'rgba(255, 255, 255, 0.1)' },
        },
      },
      animation: {
        pulse1: 'pulse1 1.2s infinite',
        pulse2: 'pulse2 1.2s infinite',
        pulse3: 'pulse3 1.2s infinite',
        fadeIn: 'fadeIn 0.3s ease-out',
        slideIn: 'slideIn 0.3s ease-out',
        glass: 'glass 0.2s ease-out',
      },
      backdropBlur: {
        xs: '2px',
        sm: '4px',
        md: '8px',
        lg: '12px',
        xl: '16px',
        '2xl': '24px',
        '3xl': '40px',
      },
    },
  },
  important: true,
  darkMode: 'class',
  /**
   * @see https://www.tailwindcss-animated.com/configurator.html
   */
  plugins: [require('tailwindcss-animated')],
};
