/**
 * Taxonomy Validation Engine
 *
 * Validates the full product taxonomy across Dragonboat and Jira:
 * - All epics have parent features.
 * - All features have parent initiatives.
 * - Required fields are populated at each hierarchy level.
 * - Naming conventions are followed.
 * - No duplicate names at the same level.
 *
 * Produces a structured report with pass/fail per rule and lists of
 * violations grouped by severity (error, warning, info).
 */

import {
  HierarchyLevel,
  HierarchyItem,
  HierarchyViolation,
  HIERARCHY,
  NAMING_CONVENTIONS,
  validateHierarchy,
  findOrphans,
} from '../mapping/hierarchy_rules';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Severity levels for taxonomy validation results. */
export type ValidationSeverity = 'error' | 'warning' | 'info';

/** Result of validating a single item. */
export interface ValidationResult {
  itemId: string;
  level: HierarchyLevel;
  valid: boolean;
  violations: HierarchyViolation[];
}

/** A single rule evaluation result within the taxonomy report. */
export interface RuleResult {
  /** Human-readable rule name. */
  rule: string;
  /** Whether the rule passed across all items. */
  passed: boolean;
  /** Number of items that violated this rule. */
  violationCount: number;
  /** The severity if the rule failed. */
  severity: ValidationSeverity;
  /** Detail messages for each violation. */
  details: string[];
}

/** Full taxonomy compliance report. */
export interface TaxonomyReport {
  /** Overall pass/fail (true only if zero errors). */
  passed: boolean;
  /** Total items audited. */
  totalItems: number;
  /** Per-rule results. */
  rules: RuleResult[];
  /** All violations grouped by severity. */
  errors: HierarchyViolation[];
  warnings: HierarchyViolation[];
  infos: HierarchyViolation[];
  /** Markdown-formatted report. */
  markdown: string;
  /** When the report was generated. */
  generatedAt: string;
}

// ---------------------------------------------------------------------------
// Validator
// ---------------------------------------------------------------------------

/**
 * Taxonomy validation engine that audits a collection of items across all
 * hierarchy levels for compliance with the product taxonomy rules.
 */
export class TaxonomyValidator {
  private items: Array<{ item: HierarchyItem; level: HierarchyLevel }>;

  /**
   * @param items - Items to validate, each paired with its hierarchy level.
   */
  constructor(items: Array<{ item: HierarchyItem; level: HierarchyLevel }>) {
    this.items = items;
  }

  // -----------------------------------------------------------------------
  // Single-item validation
  // -----------------------------------------------------------------------

  /**
   * Validate a single item at a given hierarchy level.
   *
   * @param itemId - The ID of the item to find and validate.
   * @param level - The hierarchy level to validate against.
   * @returns A {@link ValidationResult}, or `null` if the item was not found.
   */
  validateItem(itemId: string, level: HierarchyLevel): ValidationResult | null {
    const entry = this.items.find((e) => e.item.id === itemId && e.level === level);
    if (!entry) return null;

    const result = validateHierarchy(entry.item, entry.level);
    return {
      itemId,
      level,
      valid: result.valid,
      violations: result.violations,
    };
  }

  // -----------------------------------------------------------------------
  // Full validation
  // -----------------------------------------------------------------------

  /**
   * Run all taxonomy validation rules across every item and return a
   * structured {@link TaxonomyReport}.
   */
  validateAll(): TaxonomyReport {
    const allViolations: HierarchyViolation[] = [];

    // 1. Per-item hierarchy validation (required fields, parent links, naming)
    for (const { item, level } of this.items) {
      const result = validateHierarchy(item, level);
      allViolations.push(...result.violations);
    }

    // 2. Orphan check (items missing parent links)
    const orphans = findOrphans(this.items);
    // Orphan violations are already captured by validateHierarchy's parent_link
    // rule, but we add an info-level note for cross-reference.
    for (const orphan of orphans) {
      const alreadyFlagged = allViolations.some(
        (v) => v.itemId === orphan.itemId && v.rule === 'parent_link',
      );
      if (!alreadyFlagged) {
        allViolations.push({
          itemId: orphan.itemId,
          level: orphan.level,
          rule: 'parent_link',
          message: `Orphan: missing "${orphan.expectedParentField}" link`,
          severity: 'error',
        });
      }
    }

    // 3. Duplicate name check at each level
    const namesByLevel = new Map<HierarchyLevel, Map<string, string[]>>();
    for (const { item, level } of this.items) {
      const nameField = level === 'initiative' || level === 'feature' ? 'name' : 'summary';
      const name = item[nameField];
      if (typeof name !== 'string' || name.trim().length === 0) continue;

      if (!namesByLevel.has(level)) namesByLevel.set(level, new Map());
      const levelNames = namesByLevel.get(level)!;
      const normalised = name.trim().toLowerCase();
      if (!levelNames.has(normalised)) levelNames.set(normalised, []);
      levelNames.get(normalised)!.push(item.id);
    }

    for (const [level, names] of namesByLevel) {
      for (const [name, ids] of names) {
        if (ids.length > 1) {
          for (const id of ids) {
            allViolations.push({
              itemId: id,
              level,
              rule: 'duplicate_name',
              message: `Duplicate name "${name}" at ${level} level (${ids.length} items)`,
              severity: 'warning',
            });
          }
        }
      }
    }

    // Build rule results
    const ruleResults = this.buildRuleResults(allViolations);

    // Partition by severity
    const errors = allViolations.filter((v) => v.severity === 'error');
    const warnings = allViolations.filter((v) => v.severity === 'warning');
    const infos = allViolations.filter((v) => v.severity === 'info');

    const report: TaxonomyReport = {
      passed: errors.length === 0,
      totalItems: this.items.length,
      rules: ruleResults,
      errors,
      warnings,
      infos,
      markdown: '',
      generatedAt: new Date().toISOString(),
    };

    report.markdown = this.generateMarkdown(report);

    return report;
  }

  // -----------------------------------------------------------------------
  // Report generation
  // -----------------------------------------------------------------------

  /**
   * Generate a markdown-formatted taxonomy report.
   *
   * @param report - An optional pre-computed report. If omitted, runs
   *   {@link validateAll} first.
   */
  generateReport(report?: TaxonomyReport): string {
    const r = report ?? this.validateAll();
    return r.markdown;
  }

  // -----------------------------------------------------------------------
  // Internals
  // -----------------------------------------------------------------------

  private buildRuleResults(violations: HierarchyViolation[]): RuleResult[] {
    const ruleMap = new Map<string, HierarchyViolation[]>();
    for (const v of violations) {
      if (!ruleMap.has(v.rule)) ruleMap.set(v.rule, []);
      ruleMap.get(v.rule)!.push(v);
    }

    // Define all known rules so we report pass even when there are no violations
    const knownRules = ['required_field', 'parent_link', 'naming_convention', 'duplicate_name'];
    const results: RuleResult[] = [];

    for (const ruleName of knownRules) {
      const ruleViolations = ruleMap.get(ruleName) ?? [];
      const worstSeverity = ruleViolations.reduce<ValidationSeverity>((worst, v) => {
        if (v.severity === 'error') return 'error';
        if (v.severity === 'warning' && worst !== 'error') return 'warning';
        return worst;
      }, 'info');

      results.push({
        rule: ruleName,
        passed: ruleViolations.length === 0,
        violationCount: ruleViolations.length,
        severity: ruleViolations.length > 0 ? worstSeverity : 'info',
        details: ruleViolations.map((v) => `[${v.itemId}] ${v.message}`),
      });
    }

    return results;
  }

  private generateMarkdown(report: TaxonomyReport): string {
    const lines: string[] = [];

    lines.push('# Taxonomy Validation Report');
    lines.push('');
    lines.push(`**Status:** ${report.passed ? 'PASSED' : 'FAILED'}`);
    lines.push(`**Items audited:** ${report.totalItems}`);
    lines.push(`**Generated:** ${report.generatedAt}`);
    lines.push('');

    // Summary counts
    lines.push('## Summary');
    lines.push('');
    lines.push(`| Severity | Count |`);
    lines.push(`|----------|-------|`);
    lines.push(`| Errors   | ${report.errors.length} |`);
    lines.push(`| Warnings | ${report.warnings.length} |`);
    lines.push(`| Info     | ${report.infos.length} |`);
    lines.push('');

    // Per-rule results
    lines.push('## Rules');
    lines.push('');
    for (const rule of report.rules) {
      const icon = rule.passed ? 'PASS' : 'FAIL';
      lines.push(`### ${icon} - ${rule.rule}`);
      lines.push('');
      if (rule.passed) {
        lines.push('No violations.');
      } else {
        lines.push(`**Violations:** ${rule.violationCount} (${rule.severity})`);
        lines.push('');
        for (const detail of rule.details.slice(0, 50)) {
          lines.push(`- ${detail}`);
        }
        if (rule.details.length > 50) {
          lines.push(`- ... and ${rule.details.length - 50} more`);
        }
      }
      lines.push('');
    }

    // Error details
    if (report.errors.length > 0) {
      lines.push('## Errors (blocking)');
      lines.push('');
      for (const v of report.errors) {
        lines.push(`- **[${v.level}] ${v.itemId}**: ${v.message}`);
      }
      lines.push('');
    }

    // Warning details
    if (report.warnings.length > 0) {
      lines.push('## Warnings');
      lines.push('');
      for (const v of report.warnings) {
        lines.push(`- **[${v.level}] ${v.itemId}**: ${v.message}`);
      }
      lines.push('');
    }

    return lines.join('\n');
  }
}
