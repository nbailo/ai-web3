import type { CSSProperties } from 'react'

type Props = {
  confidence?: number
  asOf?: number
  label?: string
}

type PulseStyle = CSSProperties & {
  '--pulse-color'?: string
  '--pulse-size'?: string
  '--pulse-speed'?: string
}

export function AuroraPulse({ confidence = 0.5, asOf, label = 'confidence' }: Props) {
  const safeConfidence = Number.isFinite(confidence) ? Math.min(Math.max(confidence, 0), 1) : 0.5
  const hue = 170 + safeConfidence * 140
  const size = 220 + safeConfidence * 260
  const speed = 18 - safeConfidence * 9
  const opacity = 0.2 + safeConfidence * 0.25
  const freshness = typeof asOf === 'number' && asOf > 0 ? Date.now() - asOf : null
  const freshnessLabel =
    freshness == null
      ? 'snapshot unknown'
      : freshness < 5_000
        ? 'just now'
        : `${Math.round(freshness / 1000)}s ago`

  const style: PulseStyle = {
    '--pulse-color': `hsla(${hue}, 90%, 62%, ${opacity})`,
    '--pulse-size': `${size}px`,
    '--pulse-speed': `${Math.max(speed, 4)}s`,
  }

  return (
    <div className="aurora-pulse" style={style}>
      <div className="aurora-pulse__halo" />
      <div className="aurora-pulse__label">
        <span>{Math.round(safeConfidence * 100)}% {label}</span>
        <small>{freshnessLabel}</small>
      </div>
    </div>
  )
}
