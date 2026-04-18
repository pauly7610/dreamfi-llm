/**
 * Product Taxonomy Hierarchy Rules
 *
 * Defines and enforces the four-level product hierarchy used across
 * Dragonboat and Jira:
 *
 *   Initiative (Dragonboat)
 *     -> Feature (Dragonboat)
 *       -> Epic (Jira <-> Dragonboat)
 *         -> Story / Task / Bug (Jira only)
 *
 * Each level declares required fields and naming conventions.
 * The module exports validators that audit items for compliance.
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** The four levels of the product taxonomy. */
export type HierarchyLevel = 'initiative' | 'feature' | 'epic' | 'story';

/** A single violation found during hierarchy validation. */
export interface HierarchyViolation {
  /** The ID of the item that has the violation. */
  itemId: string;
  /** The hierarchy level the item belongs to. */
  level: HierarchyLevel;
  /** The rule that was violated. */
  rule: string;
  /** Human-readable description of the violation. */
  message: string;
  /** Severity: error blocks, warning flags, info is advisory. */
  severity: 'error' | 'warning' | 'info';
}

/** Result of validating a single item against hierarchy rules. */
export interface HierarchyValidationResult {
  /** Whether the item passes all required rules (no errors). */
  valid: boolean;
  /** The item's hierarchy level. */
  level: HierarchyLevel;
  /** All violations found. */
  violations: HierarchyViolation[];
}

/** An item at any level missing its required parent link. */
export interface OrphanItem {
  itemId: string;
  level: HierarchyLevel;
  expectedParentField: string;
}

/** Full hierarchy audit across all items. */
export interface HierarchyReport {
  /** Total items audited. */
  totalItems: number;
  /** Items passing all rules. */
  passingItems: number;
  /** Items with at least one error-level violation. */
  failingItems: number;
  /** Items with warnings but no errors. */
  warningItems: number;
  /** Orphaned items (missing parent links). */
  orphans: OrphanItem[];
  /** All violations found across all items. */
  violations: HierarchyViolation[];
  /** Timestamp of the report. */
  generatedAt: string;
}

/** Generic item shape that the hierarchy validator can inspect. */
export interface HierarchyItem {
  id: string;
  [key: string]: unknown;
}

// ---------------------------------------------------------------------------
// Hierarchy Definition
// ---------------------------------------------------------------------------

/**
 * The canonical hierarchy definition, mapping each level to its system
 * scope, parent level (if any), and required fields.
 */
export const HIERARCHY: Record<
  HierarchyLevel,
  {
    system: 'dragonboat' | 'jira' | 'both';
    parentLevel: HierarchyLevel | null;
    parentField: string | null;
    requiredFields: string[];
  }
> = {
  initiative: {
    system: 'dragonboat',
    parentLevel: null,
    parentField: null,
    requiredFields: ['name', 'owner', 'status', 'target_quarter'],
  },
  feature: {
    system: 'dragonboat',
    parentLevel: 'initiative',
    parentField: 'parent_initiative',
    requiredFields: ['name', 'owner', 'status', 'parent_initiative', 'target_date'],
  },
  epic: {
    system: 'both',
    parentLevel: 'feature',
    parentField: 'linked_feature',
    requiredFields: ['summary', 'owner', 'target_date', 'priority', 'linked_feature', 'description'],
  },
  story: {
    system: 'jira',
    parentLevel: 'epic',
    parentField: 'epic_link',
    requiredFields: ['summary', 'acceptance_criteria', 'story_points', 'sprint'],
  },
};

// ---------------------------------------------------------------------------
// Naming Conventions
// ---------------------------------------------------------------------------

/**
 * Naming convention regex per hierarchy level.
 *
 * - **Initiative**: Must start with `[Q<quarter>]` (e.g. `[Q2] User Growth`).
 * - **Feature**: Must start with `[<team>]` (e.g. `[Platform] SSO Integration`).
 * - **Epic**: Must start with the Jira project key (e.g. `DREAM-123: ...`).
 * - **Story**: No strict convention; title must be non-empty.
 */
export const NAMING_CONVENTIONS: Record<HierarchyLevel, { pattern: RegExp; description: string }> = {
  initiative: {
    pattern: /^\[Q[1-4]\]\s.+/,
    description: 'Must start with [Q<quarter>] followed by a space and name (e.g. "[Q2] User Growth")',
  },
  feature: {
    pattern: /^\[.+\]\s.+/,
    description: 'Must start with [<team>] followed by a space and name (e.g. "[Platform] SSO")',
  },
  epic: {
    pattern: /^[A-Z]+-\d+[:\s].+/,
    description: 'Must start with Jira key (e.g. "DREAM-123: Epic title")',
  },
  story: {
    pattern: /^.{3,}/,
    description: 'Must be at least 3 characters long',
  },
};

// ---------------------------------------------------------------------------
// Validation
// ---------------------------------------------------------------------------

/**
 * Validate a single item against the hierarchy rules for its level.
 *
 * Checks:
 * 1. All required fields are present and non-empty.
 * 2. The naming convention for the level is followed.
 * 3. The parent link field is populated (if the level requires one).
 *
 * @param item - The item to validate (must include an `id` property).
 * @param level - The hierarchy level to validate against.
 * @returns A {@link HierarchyValidationResult} with any violations.
 */
export function validateHierarchy(item: HierarchyItem, level: HierarchyLevel): HierarchyValidationResult {
  const violations: HierarchyViolation[] = [];
  const def = HIERARCHY[level];

  // --- Required fields ---
  for (const field of def.requiredFields) {
    const value = item[field];
    const empty =
      value === undefined ||
      value === null ||
      (typeof value === 'string' && value.trim().length === 0);

    if (empty) {
      violations.push({
        itemId: item.id,
        level,
        rule: 'required_field',
        message: `Required field "${field}" is missing or empty`,
        severity: 'error',
      });
    }
  }

  // --- Naming convention ---
  const nameField = level === 'initiative' || level === 'feature' ? 'name' : 'summary';
  const nameValue = item[nameField];
  if (typeof nameValue === 'string' && nameValue.trim().length > 0) {
    const convention = NAMING_CONVENTIONS[level];
    if (!convention.pattern.test(nameValue)) {
      violations.push({
        itemId: item.id,
        level,
        rule: 'naming_convention',
        message: `Name "${nameValue}" does not follow convention: ${convention.description}`,
        severity: 'warning',
      });
    }
  }

  // --- Parent link ---
  if (def.parentField) {
    const parentValue = item[def.parentField];
    const hasParent =
      parentValue !== undefined &&
      parentValue !== null &&
      (typeof parentValue !== 'string' || parentValue.trim().length > 0);

    if (!hasParent) {
      violations.push({
        itemId: item.id,
        level,
        rule: 'parent_link',
        message: `Missing parent link "${def.parentField}" (expected link to ${def.parentLevel} level)`,
        severity: 'error',
      });
    }
  }

  const hasErrors = violations.some((v) => v.severity === 'error');

  return {
    valid: !hasErrors,
    level,
    violations,
  };
}

/**
 * Scan a collection of items across all levels and return orphans --
 * items that are missing their required parent link.
 *
 * @param items - Array of `{ item, level }` tuples.
 * @returns Array of {@link OrphanItem} entries.
 */
export function findOrphans(
  items: Array<{ item: HierarchyItem; level: HierarchyLevel }>,
): OrphanItem[] {
  const orphans: OrphanItem[] = [];

  for (const { item, level } of items) {
    const def = HIERARCHY[level];
    if (!def.parentField) continue;

    const parentValue = item[def.parentField];
    const hasParent =
      parentValue !== undefined &&
      parentValue !== null &&
      (typeof parentValue !== 'string' || parentValue.trim().length > 0);

    if (!hasParent) {
      orphans.push({
        itemId: item.id,
        level,
        expectedParentField: def.parentField,
      });
    }
  }

  return orphans;
}

/**
 * Generate a full hierarchy audit report for a set of items.
 *
 * @param items - Array of `{ item, level }` tuples to audit.
 * @returns A {@link HierarchyReport} summarizing the audit.
 */
export function generateHierarchyReport(
  items: Array<{ item: HierarchyItem; level: HierarchyLevel }>,
): HierarchyReport {
  const allViolations: HierarchyViolation[] = [];
  let passing = 0;
  let failing = 0;
  let warnings = 0;

  for (const { item, level } of items) {
    const result = validateHierarchy(item, level);
    allViolations.push(...result.violations);

    if (result.valid && result.violations.length === 0) {
      passing++;
    } else if (!result.valid) {
      failing++;
    } else {
      warnings++;
    }
  }

  const orphans = findOrphans(items);

  return {
    totalItems: items.length,
    passingItems: passing,
    failingItems: failing,
    warningItems: warnings,
    orphans,
    violations: allViolations,
    generatedAt: new Date().toISOString(),
  };
}
