import type { CSSProperties, ReactElement } from 'react'
import type { SimpleIcon } from 'simple-icons'
import { siConfluence, siGoogleanalytics, siJira, siMetabase, siPosthog } from 'simple-icons'

type ConnectorIconProps = {
  id: string
  name: string
  size?: 'default' | 'large'
}

type BrandMark = {
  hex: string
  icon: ReactElement
}

const simpleIconById: Record<string, SimpleIcon> = {
  confluence: siConfluence,
  ga: siGoogleanalytics,
  jira: siJira,
  metabase: siMetabase,
  posthog: siPosthog,
}

const klaviyoFlagPath = 'M8651.28 0H7656.24V681.304H8651.28L8454.88 340.652L8651.28 0Z'

function KlaviyoMark() {
  return (
    <svg viewBox="7656.24 0 995.04 681.304" aria-hidden="true">
      <path d={klaviyoFlagPath} />
    </svg>
  )
}

function brandMarkFor(id: string): BrandMark | null {
  const simpleIcon = simpleIconById[id]
  if (simpleIcon) {
    return {
      hex: simpleIcon.hex,
      icon: (
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d={simpleIcon.path} />
        </svg>
      ),
    }
  }

  if (id === 'klaviyo') {
    return {
      // Klaviyo's 2022 mark is the flag from its wordmark; Simple Icons does not ship it.
      hex: '232426',
      icon: <KlaviyoMark />,
    }
  }

  return null
}

function ConnectorFallbackGlyph({ id }: { id: string }) {
  switch (id) {
    case 'dragonboat':
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M6 16.5h12l-2 2.8H8L6 16.5Zm5-11 6 8h-6v-8Zm-1.5 1.8v6.2H5.2l4.3-6.2Z" />
        </svg>
      )
    case 'netxd':
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M7 8.5a2.5 2.5 0 1 1 1.7 2.4l2 2.6a2.6 2.6 0 0 1 2.6 0l2-2.6A2.5 2.5 0 1 1 17 12a2.4 2.4 0 0 1-.4 0l-2.1 2.7a2.5 2.5 0 1 1-5 0L7.4 12A2.5 2.5 0 0 1 7 8.5Z" />
        </svg>
      )
    case 'sardine':
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M12 4.5 18.5 7v5.1c0 3.7-2.5 6.4-6.5 7.4-4-1-6.5-3.7-6.5-7.4V7L12 4.5Zm-3 7.7 2.2 2.2L15.5 10l-1.2-1.2-3.1 3.1-1-1-1.2 1.3Z" />
        </svg>
      )
    case 'socure':
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M5 6h14v12H5V6Zm3 3.2h4v3.6H8V9.2Zm6 0h3v1.4h-3V9.2Zm0 3h3v1.4h-3v-1.4ZM8 15h9v1.2H8V15Z" />
        </svg>
      )
    default:
      return <span>{id.slice(0, 2).toUpperCase()}</span>
  }
}

function ConnectorIcon({ id, name, size = 'default' }: ConnectorIconProps) {
  const brandMark = brandMarkFor(id)
  const style = brandMark
    ? ({ '--connector-brand-color': `#${brandMark.hex}` } as CSSProperties)
    : undefined

  return (
    <span
      className={`connector-icon connector-icon-${id}${brandMark ? ' has-brand-logo' : ''} connector-icon-${size}`}
      aria-label={`${name} connector`}
      style={style}
    >
      {brandMark ? brandMark.icon : <ConnectorFallbackGlyph id={id} />}
    </span>
  )
}

export default ConnectorIcon
