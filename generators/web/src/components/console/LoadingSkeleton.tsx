function LoadingSkeleton() {
  return (
    <div className="skeleton-page">
      <div className="skeleton-row tall" />
      <div className="skeleton-grid four">
        <div className="skeleton-row" />
        <div className="skeleton-row" />
        <div className="skeleton-row" />
        <div className="skeleton-row" />
      </div>
      <div className="skeleton-grid two">
        <div className="skeleton-row large" />
        <div className="skeleton-row large" />
      </div>
    </div>
  )
}

export default LoadingSkeleton
