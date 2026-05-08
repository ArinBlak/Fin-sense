import { type ReactNode } from 'react'

interface Props { children: ReactNode; className?: string }

export default function Card({ children, className = '' }: Props) {
  return (
    <div
      className={`rounded-2xl p-6 ${className}`}
      style={{ background: '#15293A', border: '1px solid rgba(255,255,255,0.06)' }}
    >
      {children}
    </div>
  )
}
