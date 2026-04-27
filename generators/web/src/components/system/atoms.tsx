import type { ReactNode } from 'react'

export type ConnectorKey =
  | 'jira'
  | 'posthog'
  | 'metabase'
  | 'klaviyo'
  | 'confluence'
  | 'socure'
  | 'sardine'
  | 'ga'
  | 'dragonboat'
  | 'netxd'
  | 'generic'

const CONNECTOR_LETTERS: Record<ConnectorKey, string> = {
  jira: 'J',
  posthog: 'P',
  metabase: 'M',
  klaviyo: 'K',
  confluence: 'C',
  socure: 'S',
  sardine: 'Sa',
  ga: 'GA',
  dragonboat: 'D',
  netxd: 'N',
  generic: '?',
}

export function connectorKeyFromId(value: string | null | undefined): ConnectorKey {
  switch (value) {
    case 'jira':
    case 'posthog':
    case 'metabase':
    case 'klaviyo':
    case 'confluence':
    case 'socure':
    case 'sardine':
    case 'ga':
    case 'dragonboat':
    case 'netxd':
      return value
    default:
      return 'generic'
  }
}

export function ConnectorLogo({
  connector,
  label,
  size = 'sm',
}: {
  connector: ConnectorKey
  label?: string
  size?: 'sm' | 'lg'
}) {
  const text = CONNECTOR_LETTERS[connector] ?? label?.slice(0, 2).toUpperCase() ?? '?'
  return (
    <span className={`clogo clogo-${connector}${size === 'lg' ? ' lg' : ''}`} aria-hidden="true">
      {text}
    </span>
  )
}

export type ChipTone = 'default' | 'ready' | 'warn' | 'bad' | 'signal'

export function Chip({
  children,
  dot = true,
  tone = 'default',
}: {
  children: ReactNode
  dot?: boolean
  tone?: ChipTone
}) {
  const toneClass = tone === 'default' ? '' : `chip-${tone}`
  return (
    <span className={`chip ${toneClass}`.trim()}>
      {dot ? <span className="dot" /> : null}
      {children}
    </span>
  )
}

export function Cite({
  connector,
  href,
  label,
}: {
  connector: ConnectorKey
  href?: string
  label: string
}) {
  const content = (
    <>
      <ConnectorLogo connector={connector} />
      <span>{label}</span>
    </>
  )

  if (href) {
    return (
      <a className="cite" href={href}>
        {content}
      </a>
    )
  }

  return <span className="cite">{content}</span>
}

export function KPI({
  delta,
  deltaTone,
  label,
  source,
  value,
}: {
  delta?: string
  deltaTone?: 'up' | 'down' | 'flat'
  label: string
  source?: { connector: ConnectorKey; href?: string; label: string }
  value: ReactNode
}) {
  return (
    <div className="kpi">
      <span className="lbl">{label}</span>
      <span className="val">{value}</span>
      {delta ? <span className={`delta ${deltaTone ?? ''}`.trim()}>{delta}</span> : null}
      {source ? (
        <span className="src">
          <Cite connector={source.connector} href={source.href} label={source.label} />
        </span>
      ) : null}
    </div>
  )
}

export function Spark({ hiAt, values }: { hiAt?: number; values: number[] }) {
  const safeValues = values.length > 0 ? values : [0]
  const max = Math.max(...safeValues, 1)

  return (
    <div className="bars" aria-hidden="true">
      {safeValues.map((value, index) => (
        <span
          key={`${value}-${index}`}
          className={index === hiAt ? 'hi' : ''}
          style={{ height: `${Math.max(2, (value / max) * 22)}px` }}
        />
      ))}
    </div>
  )
}

export function SectionHead({
  eyebrow,
  right,
  title,
}: {
  eyebrow?: string
  right?: ReactNode
  title: ReactNode
}) {
  return (
    <div className="section-head">
      <h3>
        {eyebrow ? <span className="eyebrow">{eyebrow}</span> : null}
        <span>{title}</span>
      </h3>
      {right}
    </div>
  )
}
