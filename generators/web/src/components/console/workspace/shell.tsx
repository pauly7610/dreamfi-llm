import type { ReactNode } from 'react'

import type { ProductTopic } from '../../../content/productTopics'
import type { ConnectorWorkspacePayload } from '../../../types/connectorWorkspace'
import { askHref } from './links'
import type { WorkspaceRendererProps } from './types'

type WorkspaceLink = {
  href: string
  label: string
}

type WorkspaceStatus = {
  label: string
  tone: 'active' | 'neutral' | 'warning'
}

type ConnectorWorkspaceShellProps = WorkspaceRendererProps & {
  children: ReactNode
  eyebrow: string
  outerClassName: string
  shellClassName?: string
  showNavigation?: boolean
  showStatus?: boolean
}

function navLinks(workspace: ConnectorWorkspacePayload): WorkspaceLink[] {
  return [
    ...workspace.sections.map((section) => ({ href: `#${section.id}`, label: section.label })),
    { href: '#source-context', label: 'Context' },
  ]
}

function statusTone(status: ConnectorWorkspacePayload['connector']['status']): WorkspaceStatus['tone'] {
  if (status === 'degraded' || status === 'not_configured') {
    return 'warning'
  }
  if (status === 'available') {
    return 'neutral'
  }
  return 'active'
}

function statusSummary(workspace: ConnectorWorkspacePayload): WorkspaceStatus[] {
  return [
    { label: workspace.connector.freshness, tone: statusTone(workspace.connector.status) },
    { label: workspace.connector.primaryDataset, tone: 'neutral' },
    {
      label:
        workspace.connector.status === 'connected'
          ? 'Live source'
          : workspace.connector.status === 'available'
            ? 'Preview source'
            : 'Needs review',
      tone: statusTone(workspace.connector.status),
    },
  ]
}

function TopicsBlock({ relatedTopics }: { relatedTopics: ProductTopic[] }) {
  if (relatedTopics.length === 0) {
    return null
  }

  return (
    <section className="connector-topic-block">
      <span className="eyebrow">Connected rooms</span>
      <div className="connector-topic-list">
        {relatedTopics.map((topic) => (
          <a key={topic.id} href={`/console/topics/${topic.id}`}>
            <strong>{topic.title}</strong>
            <small>{topic.question}</small>
          </a>
        ))}
      </div>
    </section>
  )
}

function WorkflowBlock({ workspace }: { workspace: ConnectorWorkspacePayload }) {
  return (
    <section className="connector-topic-block">
      <span className="eyebrow">Useful actions</span>
      <div className="connector-topic-list">
        {workspace.workflows.map((workflow) => (
          <a key={workflow.title} href={workflow.href}>
            <strong>{workflow.title}</strong>
            <small>{workflow.detail}</small>
          </a>
        ))}
      </div>
    </section>
  )
}

function ContextRail({ relatedTopics, workspace }: WorkspaceRendererProps) {
  const starterQuestion = workspace.questions[0] ?? `What should Product know from ${workspace.connector.name}?`
  const sourceId = workspace.connector.id
  const sourceName = workspace.connector.name

  return (
    <aside id="source-context" className="connector-context-rail">
      <section className="connector-topic-block">
        <span className="eyebrow">In scope</span>
        <div className="connector-chip-row">
          {workspace.views.map((view) => (
            <a key={view} className="connector-chip" href={askHref(sourceId, `What should Product know from the ${view} in ${sourceName}?`)}>
              {view}
            </a>
          ))}
        </div>
      </section>
      <section className="connector-topic-block">
        <span className="eyebrow">What Product should inspect</span>
        <div className="connector-note-list">
          {workspace.inspect.map((item) => (
            <a
              key={item.title}
              className="connector-note-link"
              href={askHref(sourceId, `What should Product inspect about ${item.title} in ${sourceName}?`)}
            >
              <strong>{item.title}</strong>
              <p>{item.detail}</p>
            </a>
          ))}
        </div>
      </section>
      <TopicsBlock relatedTopics={relatedTopics} />
      <WorkflowBlock workspace={workspace} />
      <section className="connector-topic-block">
        <span className="eyebrow">Question to start with</span>
        <a className="connector-side-question connector-side-question-link" href={askHref(sourceId, starterQuestion)}>
          {starterQuestion}
        </a>
      </section>
    </aside>
  )
}

export function ConnectorWorkspaceShell({
  children,
  eyebrow,
  outerClassName,
  relatedTopics,
  shellClassName,
  showNavigation = true,
  showStatus = true,
  workspace,
}: ConnectorWorkspaceShellProps) {
  return (
    <section id="source-data" className={`connector-workspace ${outerClassName} panel`}>
      <div className="connector-workspace-header">
        <div>
          <span className="eyebrow">{eyebrow}</span>
          <h2>{workspace.connector.workspaceTitle}</h2>
          <p>{workspace.connector.workspaceDescription}</p>
        </div>
        {showNavigation ? (
          <nav className="connector-workspace-tabs" aria-label={`${workspace.connector.name} workspace sections`}>
            {navLinks(workspace).map((link) => (
              <a key={link.label} href={link.href}>
                {link.label}
              </a>
            ))}
          </nav>
        ) : null}
      </div>
      {showStatus ? (
        <div className="connector-status-row">
          {statusSummary(workspace).map((item) => (
            <span key={item.label} className={`connector-status-pill tone-${item.tone}`}>
              {item.label}
            </span>
          ))}
        </div>
      ) : null}
      <div className={`connector-shell${shellClassName ? ` ${shellClassName}` : ''}`}>
        <div className="connector-main">{children}</div>
        <ContextRail relatedTopics={relatedTopics} workspace={workspace} />
      </div>
    </section>
  )
}
