/**
 * Shared type definitions for the DreamFi Generators service.
 *
 * These types define the structure of skill templates, hard-gate constraints,
 * and form fields used by every generator in the catalog.
 */

// ---------------------------------------------------------------------------
// Hard Gates
// ---------------------------------------------------------------------------

/**
 * A single binary evaluation criterion. The `check` function receives the
 * raw generator output and returns `true` when the output passes.
 *
 * Hard gates are locked after creation -- they are never modified during
 * optimization rounds. Only the prompt is changed; the gates stay fixed.
 */
export interface HardGate {
  /** Unique key within the skill, e.g. "word_limit" */
  key: string;
  /** Human-readable description shown in eval results */
  description: string;
  /** Binary pass/fail check executed against the generated output */
  check: (output: string) => boolean;
}

// ---------------------------------------------------------------------------
// Form Fields
// ---------------------------------------------------------------------------

/** Supported HTML-style input types for generator forms. */
export type FormFieldType =
  | 'text'
  | 'textarea'
  | 'select'
  | 'multiselect'
  | 'number'
  | 'date';

/**
 * Describes a single input field on the generator form. The generator
 * service uses these definitions to validate incoming form data before
 * building the prompt.
 */
export interface FormField {
  /** Field identifier used as the key in submitted form data */
  name: string;
  /** Display label shown to the user */
  label: string;
  /** Input control type */
  type: FormFieldType;
  /** Whether the field must be filled before generation */
  required: boolean;
  /** Placeholder / example text */
  placeholder?: string;
  /** Option values for select / multiselect fields */
  options?: string[];
  /** Maximum character length for text / textarea fields */
  maxLength?: number;
}

// ---------------------------------------------------------------------------
// Skill Template
// ---------------------------------------------------------------------------

/** Tier levels indicating skill complexity and gate count. */
export type SkillTier = 1 | 2 | 3;

/** Allowed output formats for generated content. */
export type OutputFormat = 'markdown' | 'plaintext' | 'html';

/**
 * Complete configuration for a single generator skill.
 *
 * A SkillTemplate bundles everything the generation engine needs:
 * the prompt, the hard gates, the form schema, and output constraints.
 */
export interface SkillTemplate {
  /** Unique identifier, e.g. "cold_email" */
  skillName: string;
  /** Logical grouping, e.g. "content", "internal", "outreach" */
  skillFamily: string;
  /** Complexity tier (1 = foundational, 3 = specialized) */
  tier: SkillTier;
  /** One-line description of what this generator produces */
  description: string;
  /** Locked binary evaluation criteria */
  hardGates: HardGate[];
  /** Form field definitions for user input */
  formFields: FormField[];
  /** System prompt template -- uses `{{fieldName}}` placeholders */
  systemPrompt: string;
  /** Output format for the generated content */
  outputFormat: OutputFormat;
  /** Optional word-count constraints applied as an additional gate */
  wordLimit?: { min: number; max: number };
}

// ---------------------------------------------------------------------------
// Constraint / Gate Results
// ---------------------------------------------------------------------------

/** Result of evaluating a single hard gate against a generated output. */
export interface GateResult {
  /** Hard-gate key */
  gate: string;
  /** Whether the output passed this gate */
  passed: boolean;
  /** Human-readable detail (e.g. "Word count: 62 (limit 75)") */
  detail: string;
}

/** Aggregated result of all constraint checks for one generation. */
export interface ConstraintResult {
  /** True only when every gate passed */
  passed: boolean;
  /** Per-gate breakdown */
  results: GateResult[];
  /** Total word count of the output */
  wordCount: number;
}

// ---------------------------------------------------------------------------
// Generation Results
// ---------------------------------------------------------------------------

/** Result returned by the generation engine for a single output. */
export interface GenerationResult {
  /** The generated text */
  output: string;
  /** Whether every hard gate passed */
  passedAllGates: boolean;
  /** Per-gate breakdown */
  gateResults: GateResult[];
  /** Total word count */
  wordCount: number;
  /** Skill that produced the output */
  skillName: string;
  /** ISO-8601 timestamp of generation */
  timestamp: string;
}

// ---------------------------------------------------------------------------
// Eval Round Results
// ---------------------------------------------------------------------------

/** Failure breakdown entry for a single gate across a round. */
export interface GateFailureSummary {
  gate: string;
  failCount: number;
  totalChecks: number;
}

/** Result of a full eval round (autoresearch pattern). */
export interface RoundResult {
  /** Unique identifier for this round */
  roundId: string;
  /** Aggregate score: total passes / total checks */
  score: number;
  /** Score from the previous best round (null on first run) */
  previousScore: number | null;
  /** Whether the prompt change was kept (score improved) */
  kept: boolean;
  /** All generated outputs with their gate results */
  outputs: GenerationResult[];
  /** Per-gate failure summary */
  failureBreakdown: GateFailureSummary[];
}
