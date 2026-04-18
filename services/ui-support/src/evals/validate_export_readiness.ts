/**
 * Export Readiness Validation
 *
 * An artifact is ONLY export-ready when BOTH code and copy pass.
 * Code checks enforce responsive, semantic, standard-component usage.
 * Copy checks run the mapped skill eval and enforce hard gates.
 */

import { mapToSkill, TargetSurface } from '../intake/intake_schema';

export interface CodeCheckResult {
  ruleId: string;
  passed: boolean;
  message: string;
}

export interface CopyGateResult {
  gate: string;
  passed: boolean;
  message: string;
}

export interface CodeReadiness {
  passed: boolean;
  results: CodeCheckResult[];
}

export interface CopyReadiness {
  passed: boolean;
  skillUsed: string;
  gateResults: CopyGateResult[];
}

export interface ExportReadiness {
  codeReady: boolean;
  copyReady: boolean;
  overallReady: boolean;
  blockers: string[];
}

export interface ExportArtifact {
  html: string;
  css: string;
  copyText: string;
  targetSurface: TargetSurface;
  metadata: Record<string, unknown>;
}

/**
 * ExportReadinessChecker validates that UI artifacts meet both code
 * and copy quality bars before they can be exported/published.
 */
export class ExportReadinessChecker {
  /**
   * Validate code readiness: standard components, responsive, semantic, no inline styles.
   */
  validateCodeReadiness(artifact: ExportArtifact): CodeReadiness {
    const results: CodeCheckResult[] = [];
    const html = artifact.html;
    const css = artifact.css;

    // Check: no hard-coded pixel positioning
    const hasAbsolutePositioning = /position\s*:\s*(absolute|fixed)/.test(css);
    const hasPixelTopLeft = /(top|left|right|bottom)\s*:\s*\d+px/.test(css);
    results.push({
      ruleId: 'no-hardcoded-pixels',
      passed: !(hasAbsolutePositioning && hasPixelTopLeft),
      message: hasAbsolutePositioning && hasPixelTopLeft
        ? 'Hard-coded pixel positioning detected. Use relative/flex/grid layout.'
        : 'No hard-coded pixel positioning.',
    });

    // Check: responsive layout (flex, grid, or media queries)
    const hasResponsive =
      /display\s*:\s*(flex|grid)/.test(css) || /@media/.test(css);
    results.push({
      ruleId: 'responsive-layout',
      passed: hasResponsive,
      message: hasResponsive
        ? 'Responsive layout patterns detected.'
        : 'No responsive layout found. Use flex, grid, or media queries.',
    });

    // Check: no inline styles
    const hasInlineStyles = /style\s*=\s*"[^"]+"/i.test(html);
    results.push({
      ruleId: 'no-inline-styles',
      passed: !hasInlineStyles,
      message: hasInlineStyles
        ? 'Inline styles detected. Move styles to CSS.'
        : 'No inline styles found.',
    });

    // Check: semantic HTML
    const semanticTags = ['header', 'main', 'footer', 'nav', 'section', 'article'];
    const usesSemanticHtml = semanticTags.some(tag =>
      html.toLowerCase().includes(`<${tag}`)
    );
    results.push({
      ruleId: 'semantic-html',
      passed: usesSemanticHtml,
      message: usesSemanticHtml
        ? 'Semantic HTML elements used.'
        : 'No semantic HTML found. Use header, main, nav, section, etc.',
    });

    // Check: uses standard layout components (not custom absolute-positioned divs)
    const usesStandardComponents =
      /class\s*=\s*"[^"]*\b(card|btn|button|form|table|grid|container)\b/i.test(html) ||
      /<(button|table|form|input|select|textarea)/i.test(html);
    results.push({
      ruleId: 'standard-components',
      passed: usesStandardComponents,
      message: usesStandardComponents
        ? 'Standard layout components detected.'
        : 'No standard components found. Prefer buttons, cards, tables, forms.',
    });

    const passed = results.every(r => r.passed);
    return { passed, results };
  }

  /**
   * Validate copy readiness: maps artifact to skill, runs skill eval hard gates.
   */
  validateCopyReadiness(
    artifact: ExportArtifact,
    targetSurface: TargetSurface
  ): CopyReadiness {
    const skillName = mapToSkill(targetSurface);
    const gateResults: CopyGateResult[] = [];
    const copyText = artifact.copyText;

    // Common hard gates applied across all skills
    gateResults.push({
      gate: 'non-empty',
      passed: copyText.trim().length > 0,
      message: copyText.trim().length > 0 ? 'Copy is non-empty.' : 'Copy text is empty.',
    });

    // Skill-specific hard gates
    switch (skillName) {
      case 'landing_page_copy':
        gateResults.push({
          gate: 'no-buzzwords',
          passed: !containsBuzzwords(copyText),
          message: containsBuzzwords(copyText)
            ? 'Copy contains banned buzzwords.'
            : 'Copy is free of buzzwords.',
        });
        gateResults.push({
          gate: 'has-specific-number',
          passed: /\d+/.test(copyText),
          message: /\d+/.test(copyText)
            ? 'Copy includes a specific number.'
            : 'Copy missing a specific number or measurable result.',
        });
        gateResults.push({
          gate: 'word-count',
          passed: wordCount(copyText) >= 80 && wordCount(copyText) <= 150,
          message: `Word count: ${wordCount(copyText)} (required: 80-150).`,
        });
        break;

      case 'support_agent':
        gateResults.push({
          gate: 'under-120-words',
          passed: wordCount(copyText) <= 120,
          message: `Word count: ${wordCount(copyText)} (max: 120).`,
        });
        break;

      case 'meeting_summary':
        gateResults.push({
          gate: 'under-300-words',
          passed: wordCount(copyText) <= 300,
          message: `Word count: ${wordCount(copyText)} (max: 300).`,
        });
        gateResults.push({
          gate: 'has-sections',
          passed: /##|###|\*\*decisions\*\*|\*\*action items\*\*/i.test(copyText),
          message: 'Summary must have distinct sections for decisions and action items.',
        });
        break;

      case 'newsletter_headline':
        gateResults.push({
          gate: 'under-50-chars',
          passed: copyText.split('\n')[0].length <= 50,
          message: `Subject line length: ${copyText.split('\n')[0].length} (max: 50).`,
        });
        gateResults.push({
          gate: 'has-number',
          passed: /\d+/.test(copyText.split('\n')[0]),
          message: 'Subject line must include a specific number.',
        });
        break;

      case 'product_description':
        gateResults.push({
          gate: 'word-count',
          passed: wordCount(copyText) >= 100 && wordCount(copyText) <= 200,
          message: `Word count: ${wordCount(copyText)} (required: 100-200).`,
        });
        gateResults.push({
          gate: 'no-competitor-comparison',
          passed: !/unlike|compared to|better than|versus/i.test(copyText),
          message: 'Product description must be free of competitor comparisons.',
        });
        break;

      case 'cold_email':
        gateResults.push({
          gate: 'under-75-words',
          passed: wordCount(copyText) <= 75,
          message: `Word count: ${wordCount(copyText)} (max: 75).`,
        });
        gateResults.push({
          gate: 'ends-with-question',
          passed: copyText.trim().endsWith('?'),
          message: 'Cold email must end with a question.',
        });
        break;
    }

    const passed = gateResults.every(g => g.passed);
    return { passed, skillUsed: skillName, gateResults };
  }

  /**
   * Full export readiness: both code AND copy must pass.
   */
  validateExportReadiness(artifact: ExportArtifact): ExportReadiness {
    const codeResult = this.validateCodeReadiness(artifact);
    const copyResult = this.validateCopyReadiness(artifact, artifact.targetSurface);

    const blockers: string[] = [];
    for (const r of codeResult.results) {
      if (!r.passed) blockers.push(`[CODE] ${r.message}`);
    }
    for (const g of copyResult.gateResults) {
      if (!g.passed) blockers.push(`[COPY] ${g.message}`);
    }

    return {
      codeReady: codeResult.passed,
      copyReady: copyResult.passed,
      overallReady: codeResult.passed && copyResult.passed,
      blockers,
    };
  }
}

// --- Helpers ---

const BUZZWORDS = [
  'revolutionary', 'cutting-edge', 'synergy', 'next-level', 'game-changing',
  'leverage', 'unlock', 'transform', 'streamline', 'empower', 'innovative',
  'seamless', 'robust', 'scalable', 'holistic',
];

function containsBuzzwords(text: string): boolean {
  const lower = text.toLowerCase();
  return BUZZWORDS.some(bw => lower.includes(bw));
}

function wordCount(text: string): number {
  return text.trim().split(/\s+/).filter(w => w.length > 0).length;
}
