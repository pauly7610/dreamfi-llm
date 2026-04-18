/**
 * Jira <-> Dragonboat Field Mapping
 *
 * Defines the canonical mapping between Jira issue fields and Dragonboat
 * feature fields. Each mapping entry declares the source/target field names,
 * the type of mapping (direct, transform, or lookup), and an optional
 * transform function.
 */

import { mapJiraStatus } from './jira_status_map';
import { DragonboatStatus } from './dragonboat_status_map';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** How a field value is translated between systems. */
export type MappingType = 'direct' | 'transform' | 'lookup';

/** A single field-level mapping rule. */
export interface FieldMapping {
  /** The Jira field key (e.g. `status`, `priority`, `fixVersions`). */
  jiraField: string;
  /** The corresponding Dragonboat field name. */
  dragonboatField: string;
  /** The strategy used to convert the value. */
  mappingType: MappingType;
  /** Optional transform applied to the Jira value to produce the Dragonboat value. */
  transformFn?: (value: unknown) => unknown;
}

/** Flat representation of mapped Dragonboat fields. */
export interface DragonboatFields {
  progressStatus: DragonboatStatus | null;
  priority: string | null;
  release: string | null;
  tags: string[];
  parentFeature: string | null;
  owner: string | null;
  targetDate: string | null;
}

/** A single field-level mismatch detected during sync validation. */
export interface FieldMismatch {
  field: string;
  jiraValue: unknown;
  dragonboatValue: unknown;
  expected: unknown;
}

/** Result of comparing a Jira issue against its linked Dragonboat feature. */
export interface SyncValidation {
  /** Whether all mapped fields are in sync. */
  inSync: boolean;
  /** List of fields that differ between the two systems. */
  mismatches: FieldMismatch[];
  /** Timestamp of the validation. */
  validatedAt: string;
}

// ---------------------------------------------------------------------------
// Approved tag list
// ---------------------------------------------------------------------------

/** Tags that are allowed to flow from Jira labels into Dragonboat. */
const APPROVED_TAGS: Set<string> = new Set([
  'mvp',
  'tech-debt',
  'compliance',
  'fraud',
  'growth',
  'onboarding',
  'platform',
  'security',
  'ux',
  'analytics',
  'infrastructure',
  'kyc',
  'payments',
  'marketing',
]);

// ---------------------------------------------------------------------------
// Priority mapping
// ---------------------------------------------------------------------------

const PRIORITY_MAP: Record<string, string> = {
  Highest: 'P0',
  High: 'P1',
  Medium: 'P2',
  Low: 'P3',
  Lowest: 'P3',
  Blocker: 'P0',
  Critical: 'P0',
  Major: 'P1',
  Minor: 'P3',
  Trivial: 'P3',
};

// ---------------------------------------------------------------------------
// Transform functions
// ---------------------------------------------------------------------------

function transformStatus(value: unknown): DragonboatStatus | null {
  if (typeof value === 'string') return mapJiraStatus(value);
  if (value && typeof value === 'object' && 'name' in value) {
    return mapJiraStatus((value as { name: string }).name);
  }
  return null;
}

function transformPriority(value: unknown): string | null {
  if (typeof value === 'string') return PRIORITY_MAP[value] ?? value;
  if (value && typeof value === 'object' && 'name' in value) {
    const name = (value as { name: string }).name;
    return PRIORITY_MAP[name] ?? name;
  }
  return null;
}

function transformFixVersion(value: unknown): string | null {
  if (Array.isArray(value) && value.length > 0) {
    return (value[0] as { name?: string }).name ?? null;
  }
  if (value && typeof value === 'object' && 'name' in value) {
    return (value as { name: string }).name;
  }
  return typeof value === 'string' ? value : null;
}

function transformLabels(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return (value as string[]).filter((label) => APPROVED_TAGS.has(label.toLowerCase()));
}

function transformEpicLink(value: unknown): string | null {
  if (typeof value === 'string') return value;
  if (value && typeof value === 'object' && 'key' in value) {
    return (value as { key: string }).key;
  }
  return null;
}

function transformAssignee(value: unknown): string | null {
  if (typeof value === 'string') return value;
  if (value && typeof value === 'object') {
    const obj = value as Record<string, unknown>;
    return (obj.displayName as string) ?? (obj.name as string) ?? null;
  }
  return null;
}

function transformDate(value: unknown): string | null {
  if (typeof value === 'string') return value;
  if (value instanceof Date) return value.toISOString().split('T')[0];
  return null;
}

// ---------------------------------------------------------------------------
// Canonical mapping table
// ---------------------------------------------------------------------------

/**
 * Ordered list of field mappings from Jira to Dragonboat.
 *
 * Each entry defines how a Jira field value is translated into the
 * corresponding Dragonboat field. The `transformFn` is called with the
 * raw Jira field value and must return the Dragonboat-compatible value.
 */
export const FIELD_MAPPINGS: FieldMapping[] = [
  {
    jiraField: 'status',
    dragonboatField: 'progressStatus',
    mappingType: 'transform',
    transformFn: transformStatus,
  },
  {
    jiraField: 'priority',
    dragonboatField: 'priority',
    mappingType: 'transform',
    transformFn: transformPriority,
  },
  {
    jiraField: 'fixVersions',
    dragonboatField: 'release',
    mappingType: 'transform',
    transformFn: transformFixVersion,
  },
  {
    jiraField: 'labels',
    dragonboatField: 'tags',
    mappingType: 'transform',
    transformFn: transformLabels,
  },
  {
    jiraField: 'customfield_10014', // Epic Link
    dragonboatField: 'parentFeature',
    mappingType: 'transform',
    transformFn: transformEpicLink,
  },
  {
    jiraField: 'assignee',
    dragonboatField: 'owner',
    mappingType: 'transform',
    transformFn: transformAssignee,
  },
  {
    jiraField: 'duedate',
    dragonboatField: 'targetDate',
    mappingType: 'transform',
    transformFn: transformDate,
  },
];

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Map all configured fields from a raw Jira issue to Dragonboat field values.
 *
 * @param jiraIssue - A Jira issue object (must contain a `fields` property).
 * @returns A {@link DragonboatFields} object with all mapped values.
 */
export function mapFields(jiraIssue: Record<string, unknown>): DragonboatFields {
  const fields = (jiraIssue.fields ?? jiraIssue) as Record<string, unknown>;

  const result: Record<string, unknown> = {};

  for (const mapping of FIELD_MAPPINGS) {
    const rawValue = fields[mapping.jiraField];
    if (mapping.transformFn) {
      result[mapping.dragonboatField] = mapping.transformFn(rawValue);
    } else {
      result[mapping.dragonboatField] = rawValue ?? null;
    }
  }

  return {
    progressStatus: (result.progressStatus as DragonboatStatus) ?? null,
    priority: (result.priority as string) ?? null,
    release: (result.release as string) ?? null,
    tags: (result.tags as string[]) ?? [],
    parentFeature: (result.parentFeature as string) ?? null,
    owner: (result.owner as string) ?? null,
    targetDate: (result.targetDate as string) ?? null,
  };
}

/**
 * Validate that a Jira issue and its linked Dragonboat feature are in sync
 * across all mapped fields.
 *
 * @param jiraIssue - The raw Jira issue object.
 * @param dragonboatFeature - The Dragonboat feature to compare against.
 * @returns A {@link SyncValidation} with a list of mismatches.
 */
export function validateFieldSync(
  jiraIssue: Record<string, unknown>,
  dragonboatFeature: Record<string, unknown>,
): SyncValidation {
  const mapped = mapFields(jiraIssue);
  const mismatches: FieldMismatch[] = [];

  for (const mapping of FIELD_MAPPINGS) {
    const expectedValue = (mapped as Record<string, unknown>)[mapping.dragonboatField];
    const actualValue = dragonboatFeature[mapping.dragonboatField];

    const expectedStr = JSON.stringify(expectedValue);
    const actualStr = JSON.stringify(actualValue);

    if (expectedStr !== actualStr) {
      mismatches.push({
        field: mapping.dragonboatField,
        jiraValue: expectedValue,
        dragonboatValue: actualValue,
        expected: expectedValue,
      });
    }
  }

  return {
    inSync: mismatches.length === 0,
    mismatches,
    validatedAt: new Date().toISOString(),
  };
}
