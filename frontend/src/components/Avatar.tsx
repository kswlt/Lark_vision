import { useState } from 'react'

interface AvatarProps {
  name?: string
  url?: string
  size?: number
  className?: string
}

export default function Avatar({ name, url, size = 32, className = '' }: AvatarProps) {
  const [broken, setBroken] = useState(false)
  const initial = (name || '?').trim().charAt(0).toUpperCase()

  if (url && !broken) {
    return (
      <img
        src={url}
        alt={name || ''}
        width={size}
        height={size}
        style={{ width: size, height: size }}
        className={`rounded-full object-cover bg-base-700 ring-1 ring-base-600 ${className}`}
        onError={() => setBroken(true)}
      />
    )
  }
  return (
    <div
      style={{ width: size, height: size }}
      className={`rounded-full bg-base-700 text-gray-300 ring-1 ring-base-600 flex items-center justify-center font-medium select-none ${className}`}
    >
      {initial}
    </div>
  )
}
