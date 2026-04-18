/**
 * Jira Status Mapping
 *
 * Deterministic mapping from Jira statuses to Dragonboat statuses.
 * Every Jira status that enters the system MUST map to exactly one
 * Dragonboat status. Unmapped statuses are flagged as validation errors.
 */

import { DragonboatStatus } from './dragonboat_status_map';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Result of validating a single Jira status against the mapping table. */
export interface StatusMappingValidation {
  /** The original Jira status string that was validated. */
  jiraStatus: string;
  /** Whether the status has a known mapping. */
  valid: boolean;
  /** The Dragonboat status it maps to, or `null` if unmapped. */
  mappedTo: DragonboatStatus | null;
  /** Human-readable warnings (e.g. case-normalization applied). */
  warnings: string[];
}

// ---------------------------------------------------------------------------
// Canonical Mapping
// ---------------------------------------------------------------------------

/**
 * Exhaustive map from every known Jira status string to the corresponding
 * Dragonboat status. Keys are stored in their canonical casing; look-ups
 * are case-insensitive (see {@link mapJiraStatus}).
 */
export const JIRA_TO_DRAGONBOAT_STATUS: Record<string, DragonboatStatus> = {
  'To Do': DragonboatStatus.NotStarted,
  'Open': DragonboatStatus.NotStarted,
  'Backlog': DragonboatStatus.NotStarted,
  'New': DragonboatStatus.NotStarted,
  'In Progress': DragonboatStatus.InProgress,
  'In Review': DragonboatStatus.InProgress,
  'In QA': DragonboatStatus.InProgress,
  'Code Review': DragonboatStatus.InProgress,
  'In Development': DragonboatStatus.InProgress,
  'Done': DragonboatStatus.Completed,
  'Closed': DragonboatStatus.Completed,
  'Resolved': DragonboatStatus.Completed,
  'Released': DragonboatStatus.Completed,
  'Blocked': DragonboatStatus.AtRisk,
  'On Hold': DragonboatStatus.AtRisk,
  'Impediment': DragonboatStatus.AtRisk,
  "Won't Do": DragonboatStatus.Cancelled,
  'Cancelled': DragonboatStatus.Cancelled,
  'Declined': DragonboatStatus.Cancelled,
  'Duplicate': DragonboatStatus.Cancelled,
};

/**
 * Internal index keyed by lower-cased status for O(1) case-insensitive
 * look-ups. Built once at module load.
 */
const LOWERCASE_INDEX: Map<string, DragonboatStatus> = new Map(
  Object.entries(JIRA_TO_DRAGONBOAT_STATUS).map(([k, v]) => [k.toLowerCase(), v]),
);

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Map a Jira status string to its Dragonboat equivalent.
 *
 * Look-up is case-insensitive. Returns `null` when the status has no
 * mapping in {@link JIRA_TO_DRAGONBOAT_STATUS}.
 *
 * @param jiraStatus - The raw status value from a Jira issue.
 * @returns The corresponding {@link DragonboatStatus}, or `null` if unmapped.
 */
export function mapJiraStatus(jiraStatus: string): DragonboatStatus | null {
  if (!jiraStatus) return null;
  return LOWERCASE_INDEX.get(jiraStatus.trim().toLowerCase()) ?? null;
}

/**
 * Validate a single Jira status against the mapping table.
 *
 * Returns a structured result that includes:
 * - whether the mapping exists,
 * - what it maps to, and
 * - any warnings (e.g. whitespace trimming or case normalization).
 *
 * @param jiraStatus - The raw status value from a Jira issue.
 */
export function validateStatusMapping(jiraStatus: string): StatusMappingValidation {
  const warnings: string[] = [];

  if (!jiraStatus || jiraStatus.trim().length === 0) {
    return { jiraStatus, valid: false, mappedTo: null, warnings: ['Empty or blank status value'] };
  }

  const trimmed = jiraStatus.trim();
  if (trimmed !== jiraStatus) {
    warnings.push(`Leading/trailing whitespace trimmed from "${jiraStatus}"`);
  }

  const mapped = LOWERCASE_INDEX.get(trimmed.toLowerCase()) ?? null;

  // Check if the casing differed from the canonical key
  if (mapped !== null && !Object.prototype.hasOwnProperty.call(JIRA_TO_DRAGONBOAT_STATUS, trimmed)) {
    warnings.push(`Case normalized: "${trimmed}" matched via case-insensitive look-up`);
  }

  return {
    jiraStatus,
    valid: mapped !== null,
    mappedTo: mapped,
    warnings,
  };
}

/**
 * Given an array of Jira statuses, return only those that have no mapping.
 *
 * Useful for auditing Jira projects before enabling sync to detect
 * workflow customizations that need to be added to the map.
 *
 * @param jiraStatuses - Array of raw Jira status strings.
 * @returns Deduplicated array of statuses not present in the mapping table.
 */
export function getUnmappedStatuses(jiraStatuses: string[]): string[] {
  const seen = new Set<string>();
  const unmapped: string[] = [];

  for (const status of jiraStatuses) {
    const key = status.trim().toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);

    if (!LOWERCASE_INDEX.has(key)) {
      unmapped.push(status.trim());
    }
  }

  return unmapped;
}
