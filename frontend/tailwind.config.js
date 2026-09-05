/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // 工程主题：通过 CSS 变量切换浅色/深色
        base: {
          950: 'rgb(var(--base-950) / <alpha-value>)',
          900: 'rgb(var(--base-900) / <alpha-value>)',
          850: 'rgb(var(--base-850) / <alpha-value>)',
          800: 'rgb(var(--base-800) / <alpha-value>)',
          750: 'rgb(var(--base-750) / <alpha-value>)',
          700: 'rgb(var(--base-700) / <alpha-value>)',
          600: 'rgb(var(--base-600) / <alpha-value>)',
          500: 'rgb(var(--base-500) / <alpha-value>)',
          400: 'rgb(var(--base-400) / <alpha-value>)',
          300: 'rgb(var(--base-300) / <alpha-value>)'
        },
        accent: {
          DEFAULT: 'rgb(var(--accent) / <alpha-value>)',
          dim: 'rgb(var(--accent-dim) / <alpha-value>)',
          bright: 'rgb(var(--accent-bright) / <alpha-value>)',
          faint: 'rgb(var(--accent-faint) / <alpha-value>)'
        },
        gray: {
          100: 'rgb(var(--gray-100) / <alpha-value>)',
          200: 'rgb(var(--gray-200) / <alpha-value>)',
          300: 'rgb(var(--gray-300) / <alpha-value>)',
          400: 'rgb(var(--gray-400) / <alpha-value>)',
          500: 'rgb(var(--gray-500) / <alpha-value>)'
        },
        red: {
          400: 'rgb(var(--red-400) / <alpha-value>)',
          500: 'rgb(var(--red-500) / <alpha-value>)'
        },
        amber: {
          400: 'rgb(var(--amber-400) / <alpha-value>)',
          500: 'rgb(var(--amber-500) / <alpha-value>)'
        }
      },
      fontFamily: {
        mono: ['Consolas', 'Cascadia Mono', 'Menlo', 'monospace']
      }
    }
  },
  plugins: []
}
