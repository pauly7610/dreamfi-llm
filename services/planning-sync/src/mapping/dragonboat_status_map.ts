/**
 * Dragonboat Status Definitions and RAG Derivation
 *
 * Defines the canonical Dragonboat statuses used across the planning-sync
 * service and provides deterministic RAG (Red/Amber/Green) derivation
 * based on feature-level progress, blocker state, and time-to-target.
 *
 * RAG overrides without an explanatory comment are explicitly disallowed.
 */

// ---------------------------------------------------------------------------
// Enums & Types
// ---------------------------------------------------------------------------

/** Canonical set of Dragonboat feature/initiative statuses. */
export enum DragonboatStatus {
  NotStarted = 'Not Started',
  InProgress = 'In Progress',
  Completed = 'Completed',
  AtRisk = 'At Risk',
  Blocked = 'Blocked',
  Cancelled = 'Cancelled',
}

/** Traffic-light indicator derived from quantitative progress data. */
export type RAGColor = 'green' | 'amber' | 'red';

/** Structured result returned by {@link deriveRAG}. */
export interface RAGResult {
  /** The computed RAG colour. */
  color: RAGColor;
  /** Human-readable explanation of *why* this colour was chosen. */
  explanation: string;
}

/** Input data required by {@link deriveRAG} to compute RAG. */
export interface FeatureProgress {
  /** Total number of stories/tasks linked to the feature. */
  totalStories: number;
  /** Number of stories in a completed status. */
  completedStories: number;
  /** Whether any linked story is currently blocked. */
  hasBlockers: boolean;
  /** Number of consecutive calendar days the feature has been blocked. */
  blockedDays: number;
  /** Calendar days remaining until the feature target date (negative = overdue). */
  daysToTarget: number;
  /** Optional manually-set RAG colour. Rejected unless {@link ragOverrideComment} is also provided. */
  ragOverride?: RAGColor;
  /** Mandatory justification when a manual RAG override is set. */
  ragOverrideComment?: string;
}

/** Error thrown when a RAG override is attempted without a comment. */
export class RAGOverrideError extends Error {
  constructor(featureId?: string) {
    super(
      `RAG override rejected${featureId ? ` for feature ${featureId}` : ''}: ` +
        'a comment is required for every manual override',
    );
    this.name = 'RAGOverrideError';
  }
}

// ---------------------------------------------------------------------------
// RAG Derivation Rules
// ---------------------------------------------------------------------------

/**
 * Derive the RAG colour for a feature based on quantitative progress data.
 *
 * **Rules (evaluated top-to-bottom; first match wins):**
 *
 * | Colour | Condition |
 * |--------|-----------|
 * | RED    | < 50 % complete AND < 3 days to target |
 * | RED    | Blocked for > 3 consecutive days |
 * | AMBER  | 50 -- 79 % complete |
 * | AMBER  | Blockers present (but blocked <= 3 days) |
 * | AMBER  | < 7 days to target |
 * | GREEN  | >= 80 % complete AND no blockers AND >= 7 days to target |
 * | GREEN  | Completed (100 %) |
 *
 * Manual overrides are accepted **only** when accompanied by a non-empty
 * comment. Attempts to override without a comment throw a
 * {@link RAGOverrideError}.
 *
 * @param feature - Progress data for the feature.
 * @param featureId - Optional ID for error messages.
 * @returns A {@link RAGResult} with colour and explanation.
 * @throws {RAGOverrideError} If `ragOverride` is set without `ragOverrideComment`.
 */
export function deriveRAG(feature: FeatureProgress, featureId?: string): RAGResult {
  // ---- Manual override guard ----
  if (feature.ragOverride) {
    if (!feature.ragOverrideComment || feature.ragOverrideComment.trim().length === 0) {
      throw new RAGOverrideError(featureId);
    }
    return {
      color: feature.ragOverride,
      explanation: `Manual override: ${feature.ragOverrideComment}`,
    };
  }

  const pctComplete =
    feature.totalStories > 0
      ? (feature.completedStories / feature.totalStories) * 100
      : 0;

  // ---- RED conditions ----
  if (feature.blockedDays > 3) {
    return {
      color: 'red',
      explanation: `Blocked for ${feature.blockedDays} consecutive days (threshold: 3)`,
    };
  }

  if (pctComplete < 50 && feature.daysToTarget < 3) {
    return {
      color: 'red',
      explanation:
        `Only ${pctComplete.toFixed(1)}% complete with ${feature.daysToTarget} days remaining ` +
        '(requires >= 50% at 3-day mark)',
    };
  }

  // ---- GREEN shortcut: 100 % complete ----
  if (pctComplete >= 100) {
    return { color: 'green', explanation: 'All stories completed' };
  }

  // ---- AMBER conditions ----
  if (feature.hasBlockers) {
    return {
      color: 'amber',
      explanation: 'Active blocker(s) present',
    };
  }

  if (pctComplete >= 50 && pctComplete < 80) {
    return {
      color: 'amber',
      explanation: `${pctComplete.toFixed(1)}% complete (green requires >= 80%)`,
    };
  }

  if (feature.daysToTarget < 7) {
    return {
      color: 'amber',
      explanation: `${feature.daysToTarget} days to target (green requires >= 7)`,
    };
  }

  // ---- GREEN ----
  if (pctComplete >= 80 && !feature.hasBlockers && feature.daysToTarget >= 7) {
    return {
      color: 'green',
      explanation:
        `${pctComplete.toFixed(1)}% complete, no blockers, ${feature.daysToTarget} days to target`,
    };
  }

  // Fallback: less than 50 % complete but plenty of time
  if (pctComplete < 50) {
    return {
      color: 'amber',
      explanation: `${pctComplete.toFixed(1)}% complete (below 50% threshold)`,
    };
  }

  return {
    color: 'green',
    explanation: `${pctComplete.toFixed(1)}% complete, on track`,
  };
}
