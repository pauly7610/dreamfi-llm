import { useEffect, useRef } from 'react'

import { useConsoleWorkspace } from './ConsoleWorkspaceContext'

function AskPalette() {
  const {
    closeAskPalette,
    isAskPaletteOpen,
    paletteQuestion,
    paletteSourceLabel,
    paletteTopicLabel,
    recentAsks,
    reopenRecentAsk,
    setPaletteQuestion,
    submitPaletteAsk,
  } = useConsoleWorkspace()
  const textareaRef = useRef<HTMLTextAreaElement | null>(null)

  useEffect(() => {
    if (!isAskPaletteOpen) {
      return
    }

    textareaRef.current?.focus()
    textareaRef.current?.setSelectionRange(textareaRef.current.value.length, textareaRef.current.value.length)

    function handleEscape(event: KeyboardEvent) {
      if (event.key !== 'Escape') {
        return
      }

      event.preventDefault()
      closeAskPalette()
    }

    window.addEventListener('keydown', handleEscape)

    return () => {
      window.removeEventListener('keydown', handleEscape)
    }
  }, [closeAskPalette, isAskPaletteOpen])

  if (!isAskPaletteOpen) {
    return null
  }

  return (
    <div
      className="ask-palette-backdrop"
      role="presentation"
      onClick={(event) => {
        if (event.target === event.currentTarget) {
          closeAskPalette()
        }
      }}
    >
      <div className="ask-palette surface" role="dialog" aria-modal="true" aria-label="Ask DreamFi">
        <div className="section-heading">
          <div>
            <span className="eyebrow">Ask from anywhere</span>
            <h2>Keep the product thread going.</h2>
            <p className="section-subtle">
              Start from the current question, then move into grounded answers and generated work without losing context.
            </p>
          </div>
          <button type="button" className="btn btn-sm btn-ghost" onClick={closeAskPalette}>
            Close
          </button>
        </div>

        <form
          className="ask-palette-form"
          onSubmit={(event) => {
            event.preventDefault()
            submitPaletteAsk()
          }}
        >
          <label htmlFor="ask-palette-question">Question</label>
          <textarea
            ref={textareaRef}
            id="ask-palette-question"
            value={paletteQuestion}
            onChange={(event) => setPaletteQuestion(event.target.value)}
          />

          {(paletteTopicLabel || paletteSourceLabel) ? (
            <div className="ask-palette-scope">
              {paletteTopicLabel ? <span className="subtle-chip">{`Topic · ${paletteTopicLabel}`}</span> : null}
              {paletteSourceLabel ? <span className="subtle-chip">{`Source · ${paletteSourceLabel}`}</span> : null}
            </div>
          ) : null}

          <div className="ask-palette-actions">
            <button type="submit" className="btn btn-primary">Ask with receipts</button>
            <button type="button" className="btn btn-ghost" onClick={closeAskPalette}>Dismiss</button>
          </div>
        </form>

        {recentAsks.length > 0 ? (
          <section className="ask-palette-recent">
            <span className="eyebrow">Recent questions</span>
            <div className="ask-palette-recent-list">
              {recentAsks.slice(0, 3).map((recentAsk) => (
                <button
                  key={`${recentAsk.question}-${recentAsk.topicId ?? 'topic'}-${recentAsk.sourceId ?? 'source'}`}
                  type="button"
                  onClick={() => reopenRecentAsk(recentAsk)}
                >
                  {recentAsk.question}
                </button>
              ))}
            </div>
          </section>
        ) : null}
      </div>
    </div>
  )
}

export default AskPalette
