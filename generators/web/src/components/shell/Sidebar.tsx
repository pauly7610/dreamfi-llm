import type { ReactNode } from 'react'

const Icon = ({ d }: { d: string }) => (
  <svg
    width="14"
    height="14"
    viewBox="0 0 16 16"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.5"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d={d} />
  </svg>
)

const ICONS = {
  artifacts: <Icon d="M3 3h7l3 3v7a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z M10 3v3h3" />,
  ask: <Icon d="M3 10c0-3 2-5 5-5s5 2 5 5-2 5-5 5l-3 1 1-2.5" />,
  home: <Icon d="M2 7l6-5 6 5v7a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V7z" />,
  inbox: <Icon d="M2 9l2-5h8l2 5v3a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V9zM2 9h3l1 1h4l1-1h3" />,
  methodology: <Icon d="M4 3h8M4 8h8M4 13h8" />,
  source: <Icon d="M3 3h10v10H3zM3 7h10M7 3v10" />,
  topic: <Icon d="M2 4h12M2 8h12M2 12h8" />,
  trust: <Icon d="M8 1.5l5 2v4c0 3-2 5.5-5 7-3-1.5-5-4-5-7v-4l5-2z" />,
} as const

export type SidebarIcon = keyof typeof ICONS

export type NavItem = {
  count?: number | string
  dot?: 'good' | 'warn' | 'bad'
  href: string
  icon: SidebarIcon
  id: string
  label: string
}

export type NavGroup = {
  items: NavItem[]
  label?: string
}

const DOT_COLOR: Record<NonNullable<NavItem['dot']>, string> = {
  bad: 'var(--bad)',
  good: 'var(--good)',
  warn: 'var(--warn)',
}

export function Sidebar({ activeId, groups, footer }: { activeId: string; footer?: ReactNode; groups: NavGroup[] }) {
  return (
    <aside className="sidebar">
      <a className="brand" href="/console" aria-label="DreamFi home">
        <div className="brand-mark">d</div>
        <div className="brand-name">DreamFi</div>
      </a>

      {groups.map((group) => (
        <div className="nav-section" key={group.label ?? group.items.map((item) => item.id).join('|')}>
          {group.label ? <div className="nav-label">{group.label}</div> : null}
          {group.items.map((item) => (
            <a
              key={item.id}
              className={`nav-item ${activeId === item.id ? 'active' : ''}`.trim()}
              href={item.href}
            >
              <span className="nav-icon">{ICONS[item.icon]}</span>
              <span>{item.label}</span>
              {item.count !== undefined ? <span className="nav-count">{item.count}</span> : null}
              {item.dot ? <span className="nav-dot" style={{ background: DOT_COLOR[item.dot] }} /> : null}
            </a>
          ))}
        </div>
      ))}

      <div className="sidebar-footer">
        {footer ?? (
          <>
            <div className="avatar">OP</div>
            <div className="col" style={{ gap: 0 }}>
              <span style={{ color: 'var(--ink-0)', fontSize: 12 }}>Operator</span>
              <span style={{ fontSize: 11 }}>Risk and Compliance</span>
            </div>
          </>
        )}
      </div>
    </aside>
  )
}
