import type { ReactNode } from 'react'

import { Chip, type ChipTone, ConnectorLogo, type ConnectorKey } from '../system/atoms'

export type SourceTab = {
  count?: number
  id: string
  label: string
}

export function ConnectorChrome({
  actions,
  activeTab,
  connector,
  name,
  onTab,
  status,
  subtitle,
  tabs,
}: {
  actions?: ReactNode
  activeTab: string
  connector: ConnectorKey
  name: string
  onTab: (id: string) => void
  status?: { label: string; tone: Extract<ChipTone, 'ready' | 'warn' | 'bad'> }
  subtitle?: string
  tabs: SourceTab[]
}) {
  return (
    <div className="source-chrome">
      <div className="source-chrome-top">
        <ConnectorLogo connector={connector} size="lg" />
        <div className="col" style={{ gap: 2 }}>
          <div className="row" style={{ gap: 10 }}>
            <span style={{ fontSize: 15, fontWeight: 500, color: 'var(--ink-0)' }}>{name}</span>
            {status ? <Chip tone={status.tone}>{status.label}</Chip> : null}
          </div>
          {subtitle ? <span style={{ fontSize: 12, color: 'var(--ink-2)' }}>{subtitle}</span> : null}
        </div>
        <div className="spacer" />
        {actions}
      </div>

      <div className="source-chrome-tabs" role="tablist" aria-label={`${name} workspace sections`}>
        {tabs.map((tab) => (
          <button
            key={tab.id}
            className={`source-tab ${activeTab === tab.id ? 'active' : ''}`.trim()}
            onClick={() => onTab(tab.id)}
            role="tab"
            type="button"
            aria-selected={activeTab === tab.id}
          >
            {tab.label}
            {tab.count !== undefined ? (
              <span style={{ marginLeft: 6, color: 'var(--ink-3)', fontFamily: 'var(--font-mono)', fontSize: 11 }}>
                {tab.count}
              </span>
            ) : null}
          </button>
        ))}
      </div>
    </div>
  )
}
