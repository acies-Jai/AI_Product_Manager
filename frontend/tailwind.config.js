/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        zepto: {
          purple: '#5E17EB',
          light:  '#7C3AED',
          pale:   '#9F67FA',
          dark:   '#1A0533',
          bg:     '#F4F0FC',
          tint:   '#F0EAFF',
          muted:  '#EDE9FF',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
