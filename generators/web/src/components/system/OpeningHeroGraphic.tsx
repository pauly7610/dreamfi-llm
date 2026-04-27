export function OpeningHeroGraphic() {
  return (
    <svg
      viewBox="0 0 640 420"
      role="img"
      aria-label="DreamFi opening illustration"
      style={{ display: 'block', width: '100%', height: '100%' }}
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <linearGradient id="opening-hero-bg" x1="64" y1="44" x2="576" y2="376" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="rgba(184, 255, 61, 0.12)" />
          <stop offset="0.45" stopColor="rgba(108, 155, 255, 0.08)" />
          <stop offset="1" stopColor="rgba(255, 106, 91, 0.08)" />
        </linearGradient>
        <linearGradient id="opening-hero-flow" x1="170" y1="92" x2="512" y2="316" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="var(--signal)" />
          <stop offset="0.55" stopColor="var(--c-metabase)" />
          <stop offset="1" stopColor="var(--c-socure)" />
        </linearGradient>
      </defs>

      <rect x="8" y="8" width="624" height="404" rx="24" fill="var(--bg-1)" stroke="var(--line)" />
      <rect x="28" y="28" width="584" height="364" rx="18" fill="url(#opening-hero-bg)" stroke="rgba(255,255,255,0.04)" />

      <g opacity="0.95">
        <rect x="54" y="58" width="152" height="88" rx="18" fill="var(--bg-1)" stroke="var(--line-2)" />
        <text x="76" y="87" fill="var(--ink-2)" fontFamily="var(--font-mono)" fontSize="12" letterSpacing="1.1">
          ASK
        </text>
        <text x="76" y="118" fill="var(--ink-0)" fontFamily="var(--font-serif)" fontSize="28">
          Why did KYC
        </text>
        <text x="76" y="143" fill="var(--ink-0)" fontFamily="var(--font-serif)" fontSize="28">
          conversion move?
        </text>
      </g>

      <g opacity="0.9">
        <rect x="56" y="202" width="134" height="144" rx="18" fill="var(--bg-1)" stroke="var(--line-2)" />
        <text x="76" y="230" fill="var(--ink-2)" fontFamily="var(--font-mono)" fontSize="12" letterSpacing="1.1">
          SOURCES
        </text>

        <g transform="translate(76 258)">
          <circle cx="0" cy="0" r="14" fill="var(--c-metabase)" />
          <text x="-6.5" y="4.5" fill="var(--bg-0)" fontFamily="var(--font-mono)" fontSize="11" fontWeight="700">
            M
          </text>
          <text x="26" y="4.5" fill="var(--ink-1)" fontFamily="var(--font-sans)" fontSize="13">
            Metabase
          </text>
        </g>
        <g transform="translate(76 294)">
          <circle cx="0" cy="0" r="14" fill="var(--c-posthog)" />
          <text x="-6.5" y="4.5" fill="var(--bg-0)" fontFamily="var(--font-mono)" fontSize="11" fontWeight="700">
            P
          </text>
          <text x="26" y="4.5" fill="var(--ink-1)" fontFamily="var(--font-sans)" fontSize="13">
            PostHog
          </text>
        </g>
        <g transform="translate(76 330)">
          <circle cx="0" cy="0" r="14" fill="var(--c-socure)" />
          <text x="-6.5" y="4.5" fill="white" fontFamily="var(--font-mono)" fontSize="11" fontWeight="700">
            S
          </text>
          <text x="26" y="4.5" fill="var(--ink-1)" fontFamily="var(--font-sans)" fontSize="13">
            Socure
          </text>
        </g>
      </g>

      <g>
        <path
          d="M205 99C268 99 278 162 324 190C374 220 434 213 503 233"
          fill="none"
          stroke="url(#opening-hero-flow)"
          strokeWidth="3"
          strokeLinecap="round"
        />
        <path
          d="M190 275C258 275 270 255 327 255C391 255 438 289 500 289"
          fill="none"
          stroke="rgba(184,255,61,0.65)"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeDasharray="7 9"
        />
        <path
          d="M191 330C258 330 290 340 334 320C385 297 435 170 498 130"
          fill="none"
          stroke="rgba(108,155,255,0.55)"
          strokeWidth="2.5"
          strokeLinecap="round"
        />
      </g>

      <g>
        <circle cx="331" cy="225" r="68" fill="var(--bg-1)" stroke="rgba(184,255,61,0.45)" />
        <circle cx="331" cy="225" r="53" fill="rgba(184,255,61,0.08)" stroke="rgba(184,255,61,0.2)" />
        <text x="331" y="213" fill="var(--ink-2)" fontFamily="var(--font-mono)" fontSize="11" textAnchor="middle" letterSpacing="1.1">
          PRODUCT ROOM
        </text>
        <text x="331" y="244" fill="var(--ink-0)" fontFamily="var(--font-serif)" fontSize="34" textAnchor="middle">
          Grounded
        </text>
        <text x="331" y="269" fill="var(--ink-1)" fontFamily="var(--font-sans)" fontSize="13" textAnchor="middle">
          Ask → inspect → decide → publish
        </text>
      </g>

      <g opacity="0.95">
        <rect x="452" y="72" width="132" height="96" rx="18" fill="var(--bg-1)" stroke="var(--line-2)" />
        <text x="474" y="100" fill="var(--ink-2)" fontFamily="var(--font-mono)" fontSize="12" letterSpacing="1.1">
          DECISION
        </text>
        <text x="474" y="131" fill="var(--ink-0)" fontFamily="var(--font-serif)" fontSize="26">
          Hold scope
        </text>
        <text x="474" y="154" fill="var(--ink-1)" fontFamily="var(--font-sans)" fontSize="13">
          until retry evidence
        </text>
      </g>

      <g opacity="0.95">
        <rect x="436" y="228" width="154" height="118" rx="18" fill="var(--bg-1)" stroke="var(--line-2)" />
        <text x="458" y="256" fill="var(--ink-2)" fontFamily="var(--font-mono)" fontSize="12" letterSpacing="1.1">
          ARTIFACTS
        </text>
        <rect x="458" y="278" width="110" height="14" rx="7" fill="rgba(184,255,61,0.15)" />
        <rect x="458" y="302" width="92" height="14" rx="7" fill="rgba(108,155,255,0.18)" />
        <rect x="458" y="326" width="76" height="14" rx="7" fill="rgba(255,106,91,0.18)" />
        <text x="577" y="289" fill="var(--signal)" fontFamily="var(--font-mono)" fontSize="11" textAnchor="end">
          PRD
        </text>
        <text x="577" y="313" fill="var(--c-metabase)" fontFamily="var(--font-mono)" fontSize="11" textAnchor="end">
          BRIEF
        </text>
        <text x="577" y="337" fill="var(--bad)" fontFamily="var(--font-mono)" fontSize="11" textAnchor="end">
          REVIEW
        </text>
      </g>

      <g opacity="0.7">
        <circle cx="330" cy="101" r="5" fill="var(--signal)" />
        <circle cx="330" cy="349" r="5" fill="var(--c-metabase)" />
        <circle cx="489" cy="227" r="5" fill="var(--c-socure)" />
        <circle cx="205" cy="275" r="5" fill="var(--c-posthog)" />
      </g>
    </svg>
  )
}
