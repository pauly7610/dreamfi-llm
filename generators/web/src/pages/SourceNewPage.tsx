import { useEffect, useMemo, useState } from 'react'

import { getConnectorWorkspace } from '../content/connectorWorkspaces'
import type { ConnectorWorkspaceSection } from '../types/connectorWorkspace'
import type { ConsolePayload } from '../types/console'
import { useConsoleWorkspace } from '../components/console/ConsoleWorkspaceContext'
import { ConnectorChrome } from '../components/connector/ConnectorChrome'
import { Chip, Cite, KPI, SectionHead, Spark, connectorKeyFromId } from '../components/system/atoms'
import {
  labelForIntegrationStatus,
  sourceHref,
  toneForIntegrationStatus,
} from './redesignSupport'

type SourceNewPageProps = {
  data: ConsolePayload | null
  sourceId: string | null
}

function renderSectionBody(section: ConnectorWorkspaceSection) {
  if (section.table) {
    return (
      <table className="dfi-table">
        <thead>
          <tr>
            {section.table.columns.map((column) => (
              <th key={column}>{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {section.table.rows.map((row, index) => (
            <tr key={`${section.id}-row-${index}`}>
              {row.cells.map((cell, cellIndex) => (
                <td key={`${section.id}-cell-${index}-${cellIndex}`}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    )
  }

  if (section.metrics?.length) {
    return (
      <table className="dfi-table">
        <tbody>
          {section.metrics.map((metric) => (
            <tr key={metric.label}>
              <td className="strong">{metric.label}</td>
              <td className="num">{metric.value}</td>
              <td className="muted">{metric.detail}</td>
            </tr>
          ))}
        </tbody>
      </table>
    )
  }

  if (section.rows?.length) {
    return (
      <table className="dfi-table">
        <tbody>
          {section.rows.map((row) => (
            <tr key={row.label}>
              <td className="strong">{row.label}</td>
              <td className="num">{row.value}</td>
              <td className="muted">{row.detail}</td>
            </tr>
          ))}
        </tbody>
      </table>
    )
  }

  if (section.keyValues?.length) {
    return (
      <table className="dfi-table">
        <tbody>
          {section.keyValues.map((pair) => (
            <tr key={pair.label}>
              <td className="muted">{pair.label}</td>
              <td className="strong">{pair.value}</td>
            </tr>
          ))}
        </tbody>
      </table>
    )
  }

  if (section.textItems?.length) {
    return (
      <div style={{ display: 'grid', gap: 12, padding: '18px' }}>
        {section.textItems.map((item) => (
          <div key={item.title} className="surface" style={{ background: 'var(--bg-2)' }}>
            <div style={{ padding: '16px 18px' }}>
              <div className="strong">{item.title}</div>
              <div className="muted" style={{ marginTop: 6 }}>{item.detail}</div>
            </div>
          </div>
        ))}
      </div>
    )
  }

  if (section.barChart?.bars.length) {
    return (
      <div style={{ padding: '20px 18px' }}>
        <div className="row" style={{ alignItems: 'flex-end', gap: 8 }}>
          {section.barChart.bars.map((bar) => (
            <div key={bar.label} className="col" style={{ flex: 1, gap: 8, alignItems: 'center' }}>
              <div style={{ width: '100%', height: 64, display: 'flex', alignItems: 'flex-end' }}>
                <div style={{ width: '100%', height: `${Math.max(bar.value, 6)}%`, borderRadius: 6, background: section.barChart?.color }} />
              </div>
              <span className="muted" style={{ fontSize: 11, textAlign: 'center' }}>{bar.label}</span>
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (section.chart?.series[0]?.points.length) {
    const values = section.chart.series[0].points.map((point) => point.value)
    return (
      <div style={{ padding: '20px 18px' }}>
        <Spark values={values} hiAt={values.length - 1} />
      </div>
    )
  }

  if (section.timeline?.length) {
    return (
      <table className="dfi-table">
        <tbody>
          {section.timeline.map((item) => (
            <tr key={`${item.timeframe}-${item.title}`}>
              <td className="muted">{item.timeframe}</td>
              <td className="strong">{item.title}</td>
              <td>{item.tone}</td>
            </tr>
          ))}
        </tbody>
      </table>
    )
  }

  if (section.board?.length) {
    return (
      <div style={{ display: 'grid', gridTemplateColumns: `repeat(${section.board.length}, minmax(0, 1fr))`, gap: 16, padding: 18 }}>
        {section.board.map((column) => (
          <div key={column.name} className="surface" style={{ background: 'var(--bg-2)' }}>
            <SectionHead title={column.name} />
            <div style={{ display: 'grid', gap: 10, padding: 12 }}>
              {column.items.map((item) => (
                <div key={item.id} className="surface" style={{ background: 'var(--bg-1)' }}>
                  <div style={{ padding: '12px 14px' }}>
                    <div className="strong">{item.title}</div>
                    <div className="muted" style={{ marginTop: 4 }}>{`${item.id} · ${item.assignee}`}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    )
  }

  return <div className="empty-state">No section content in this development slice yet.</div>
}

function SourceDirectory({ data }: { data: ConsolePayload | null }) {
  const integrations = data?.integrations ?? []
  return (
    <div className="page">
      <div className="eyebrow" style={{ marginBottom: 12 }}>SOURCES</div>
      <h1 className="display-question" style={{ marginBottom: 24, maxWidth: 820 }}>
        Open the <em>connector workspace</em> you need.
      </h1>

      <div className="surface">
        <SectionHead title="Connected systems" eyebrow="SOURCE DIRECTORY" />
        <table className="dfi-table">
          <tbody>
            {integrations.map((integration) => (
              <tr key={integration.id}>
                <td>
                  <Cite connector={connectorKeyFromId(integration.id)} href={sourceHref(integration.id)} label={integration.name} />
                </td>
                <td className="muted">{integration.purpose}</td>
                <td>
                  <Chip tone={toneForIntegrationStatus(integration.status)}>{labelForIntegrationStatus(integration.status)}</Chip>
                </td>
                <td style={{ textAlign: 'right' }}>
                  <a className="btn btn-sm" href={sourceHref(integration.id)}>Inspect</a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export function SourceNewPage({ data, sourceId }: SourceNewPageProps) {
  const source = (data?.integrations ?? []).find((integration) => integration.id === sourceId) ?? null
  const { buildAskHref, buildGenerateHref, recommendedGeneratorSlug, recommendedGeneratorTitle } = useConsoleWorkspace()

  const workspace = useMemo(() => (source ? getConnectorWorkspace(source) : null), [source])
  const [activeTab, setActiveTab] = useState(workspace?.sections[0]?.id ?? 'overview')

  useEffect(() => {
    setActiveTab(workspace?.sections[0]?.id ?? 'overview')
  }, [workspace?.sections])

  if (!source || !workspace) {
    return <SourceDirectory data={data} />
  }

  const selectedSection = workspace.sections.find((section) => section.id === activeTab) ?? workspace.sections[0]

  return (
    <div className="col" style={{ flex: 1, minHeight: 0 }}>
      <ConnectorChrome
        connector={connectorKeyFromId(source.id)}
        name={`${source.name} workspace`}
        subtitle={workspace.connector.workspaceDescription}
        status={{ tone: toneForIntegrationStatus(source.status), label: labelForIntegrationStatus(source.status) }}
        tabs={workspace.sections.map((section) => ({ count: section.table?.rows.length, id: section.id, label: section.label }))}
        activeTab={activeTab}
        onTab={setActiveTab}
        actions={
          <>
            <a className="btn btn-sm" href={buildAskHref({ sourceId: source.id })}>Ask with this source</a>
            <a className="btn btn-sm btn-primary" href={buildGenerateHref(recommendedGeneratorSlug, { sourceId: source.id })}>{`Generate ${recommendedGeneratorTitle}`}</a>
          </>
        }
      />
      <div className="scroll" style={{ flex: 1 }}>
        <div className="page">
          <div className="surface" style={{ marginBottom: 20 }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))' }}>
              {workspace.highlights.slice(0, 4).map((highlight) => (
                <KPI key={highlight.label} label={highlight.label.toUpperCase()} value={highlight.value} delta={highlight.detail} />
              ))}
            </div>
          </div>

          <div className="surface" style={{ marginBottom: 20 }}>
            <SectionHead title={selectedSection.title} eyebrow={selectedSection.eyebrow} right={<a className="btn btn-sm btn-ghost" href={sourceHref(source.id)}>Open source route</a>} />
            {renderSectionBody(selectedSection)}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
            <div className="surface">
              <SectionHead title="Inspect next" eyebrow="GROUND THE CLAIM" />
              <table className="dfi-table">
                <tbody>
                  {workspace.inspect.map((item) => (
                    <tr key={item.title}>
                      <td className="strong">{item.title}</td>
                      <td className="muted">{item.detail}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="surface">
              <SectionHead title="Related workflows" eyebrow="CONNECT BACK TO PRODUCT" />
              <table className="dfi-table">
                <tbody>
                  {workspace.workflows.map((workflow) => (
                    <tr key={workflow.title}>
                      <td className="strong">{workflow.title}</td>
                      <td className="muted">{workflow.detail}</td>
                      <td style={{ textAlign: 'right' }}>
                        <a className="btn btn-sm" href={workflow.href}>Open</a>
                      </td>
                    </tr>
                  ))}
                  {workspace.questions.map((question) => (
                    <tr key={question}>
                      <td className="strong">{question}</td>
                      <td className="muted">Reuse this slice in Ask.</td>
                      <td style={{ textAlign: 'right' }}>
                        <a className="btn btn-sm" href={buildAskHref({ question, sourceId: source.id })}>Ask</a>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
