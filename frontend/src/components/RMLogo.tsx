/** RM 战术标识：机甲大师风格 R + 闪电，自制 SVG（无外部依赖） */
export default function RMLogo({
  size = 20,
  className = ''
}: {
  size?: number
  className?: string
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="currentColor"
      className={className}
      aria-label="RM"
    >
      {/* R 主体 */}
      <path d="M5 3h8.2c2.6 0 4.3 1.5 4.3 3.7 0 1.7-1 3-2.6 3.5l3.4 4.3h-3.2l-3-3.8H9v3.8H5V3Zm4 3.6v3.2h4a1.6 1.6 0 0 0 0-3.2H9Z" />
      {/* 闪电（R 的右腿） */}
      <path d="M14.2 14.6 18.2 18h-2.3l1.7 3.6-3.7-3.9h2l-1.7-3.1Z" />
    </svg>
  )
}
