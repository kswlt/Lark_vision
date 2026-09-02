/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // 浅色工程主题：背景浅灰、面板白、文字深灰
        base: {
          950: '#141c24',
          900: '#e9edf2',
          850: '#ffffff',
          800: '#f2f5f8',
          750: '#e9edf2',
          700: '#e3e8ee',
          600: '#d4dbe2',
          500: '#c1cbd4',
          400: '#7a8794',
          300: '#4b5966'
        },
        // 强调色：学术蓝，比深色版更深，保证白底对比度
        accent: {
          DEFAULT: '#2b6fdd',
          dim: '#1f55b8',
          bright: '#1d5fd6',
          faint: '#e4edfb'
        },
        // gray 在本项目中只作为文字色，反相为深色文字
        gray: {
          100: '#1d2733',
          200: '#2c3947',
          300: '#3f4d5b',
          400: '#5b6a78',
          500: '#75838f'
        },
        // 状态色加深，保证白底可读
        red: {
          400: '#c0392b',
          500: '#b0302a'
        },
        amber: {
          400: '#b45309',
          500: '#a16207'
        }
      },
      fontFamily: {
        mono: ['Consolas', 'Cascadia Mono', 'Menlo', 'monospace']
      }
    }
  },
  plugins: []
}
