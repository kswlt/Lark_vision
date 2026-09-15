// ESLint 9 flat config
import js from '@eslint/js'
import tseslint from 'typescript-eslint'
import reactHooks from 'eslint-plugin-react-hooks'

export default tseslint.config(
  { ignores: ['dist/**', 'node_modules/**', '*.config.*', 'postcss.config.js', 'tailwind.config.js'] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ['**/*.{ts,tsx}'],
    plugins: { 'react-hooks': reactHooks },
    rules: {
      // 只保留 hooks 基础规则（必须在顶层调用、依赖数组正确）
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn',
      // 关闭 react-compiler 激进规则（对既有大型 UI 误报多、修复风险高）
      'react-hooks/set-state-in-effect': 'off',
      'react-hooks/purity': 'off',
      'react-hooks/immutability': 'off',
      'react-hooks/use-memo': 'off',
      'react-hooks/preserve-manual-memoization': 'off',
      'react-hooks/memo-dependencies': 'off',
      'react-hooks/void-use-memo': 'off',
      'react-hooks/capitalized-calls': 'off',
      'react-hooks/static-components': 'off',
      // 项目既有风格：允许未使用变量/参数（保留为调试辅助）
      '@typescript-eslint/no-unused-vars': 'off',
      '@typescript-eslint/no-explicit-any': 'off',
      'no-empty': ['error', { allowEmptyCatch: true }]
    }
  }
)
