import type { WorkspaceChartPoint, WorkspaceChartSeries } from '../../../types/connectorWorkspace'

function coordinatesForPoints(points: WorkspaceChartPoint[], width: number, height: number, padding: number) {
  if (points.length === 0) {
    return []
  }

  const values = points.map((point) => point.value)
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1
  const usableWidth = width - padding * 2
  const usableHeight = height - padding * 2

  return points.map((point, index) => {
    const x = padding + (usableWidth * index) / Math.max(points.length - 1, 1)
    const y = padding + usableHeight - ((point.value - min) / range) * usableHeight
    return { x, y }
  })
}

function pathFromCoordinates(coords: { x: number; y: number }[]) {
  return coords.map((coord, index) => `${index === 0 ? 'M' : 'L'} ${coord.x} ${coord.y}`).join(' ')
}

function areaPathFromCoordinates(coords: { x: number; y: number }[], height: number, padding: number) {
  if (coords.length === 0) {
    return ''
  }

  const path = pathFromCoordinates(coords)
  const first = coords[0]
  const last = coords[coords.length - 1]
  const baseline = height - padding
  return `${path} L ${last.x} ${baseline} L ${first.x} ${baseline} Z`
}

export function AreaTrendChart({
  ariaLabel,
  dark = false,
  height = 180,
  series,
  width = 540,
}: {
  ariaLabel: string
  dark?: boolean
  height?: number
  series: WorkspaceChartSeries[]
  width?: number
}) {
  const padding = 18
  const allPoints = series.flatMap((entry) => entry.points)
  const yLines = 4
  const labelY = height - 4

  return (
    <div className={`chart-surface${dark ? ' dark' : ''}`}>
      <svg aria-label={ariaLabel} className="trend-chart" role="img" viewBox={`0 0 ${width} ${height}`}>
        {Array.from({ length: yLines }).map((_, index) => {
          const y = padding + ((height - padding * 2) * index) / Math.max(yLines - 1, 1)
          return <line key={y} className="trend-grid-line" x1={padding} x2={width - padding} y1={y} y2={y} />
        })}
        {series.map((entry) => {
          const coords = coordinatesForPoints(entry.points, width, height, padding)
          return (
            <g key={entry.name}>
              <path className="trend-area" d={areaPathFromCoordinates(coords, height, padding)} fill={entry.color} />
              <path className="trend-line" d={pathFromCoordinates(coords)} stroke={entry.color} />
              {coords.map((coord) => (
                <circle key={`${entry.name}-${coord.x}`} className="trend-point" cx={coord.x} cy={coord.y} fill={entry.color} r="3.25" />
              ))}
            </g>
          )
        })}
        {(allPoints.length > 0 ? allPoints.slice(0, series[0]?.points.length ?? 0) : []).map((point, index, labels) => {
          const x = padding + ((width - padding * 2) * index) / Math.max(labels.length - 1, 1)
          return (
            <text
              key={`${point.label}-${x}`}
              className="trend-axis-label"
              textAnchor={index === 0 ? 'start' : index === labels.length - 1 ? 'end' : 'middle'}
              x={x}
              y={labelY}
            >
              {point.label}
            </text>
          )
        })}
      </svg>
    </div>
  )
}

export function ColumnBarsChart({
  ariaLabel,
  bars,
  color,
}: {
  ariaLabel: string
  bars: WorkspaceChartPoint[]
  color: string
}) {
  const max = Math.max(...bars.map((bar) => bar.value), 1)

  return (
    <div className="column-chart" aria-label={ariaLabel} role="img">
      {bars.map((bar) => (
        <div key={bar.label} className="column-bar-group">
          <div className="column-bar-track">
            <div
              className="column-bar-fill"
              style={{ background: color, height: `${Math.max((bar.value / max) * 100, 10)}%` }}
            />
          </div>
          <span>{bar.label}</span>
        </div>
      ))}
    </div>
  )
}
