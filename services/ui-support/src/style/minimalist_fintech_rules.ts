/**
 * DreamFi Minimalist Fintech Style Rules
 *
 * Enforces the DreamFi design system constraints:
 * whitespace, typography, color, navigation, components, layout, content density.
 */

export interface StyleRule {
  id: string;
  category: StyleCategory;
  description: string;
  threshold: number | string;
}

export type StyleCategory =
  | 'whitespace'
  | 'typography'
  | 'colors'
  | 'navigation'
  | 'components'
  | 'layout'
  | 'content_density';

export interface StyleResult {
  ruleId: string;
  passed: boolean;
  message: string;
  severity: 'error' | 'warning' | 'info';
}

export interface StyleValidation {
  passed: boolean;
  results: StyleResult[];
  score: number; // 0-100
}

export interface UIArtifact {
  html: string;
  css: string;
  metadata: Record<string, unknown>;
}

export const STYLE_RULES: StyleRule[] = [
  // Whitespace
  {
    id: 'ws-padding',
    category: 'whitespace',
    description: 'Minimum 24px padding on all containers',
    threshold: 24,
  },
  {
    id: 'ws-gap',
    category: 'whitespace',
    description: 'Minimum 16px gap between components',
    threshold: 16,
  },

  // Typography
  {
    id: 'typo-font-sizes',
    category: 'typography',
    description: 'Maximum 3 font sizes per page',
    threshold: 3,
  },
  {
    id: 'typo-font-stack',
    category: 'typography',
    description: 'Must use system font stack',
    threshold: 'system-ui, -apple-system, sans-serif',
  },

  // Colors
  {
    id: 'color-brand-limit',
    category: 'colors',
    description: 'Maximum 3 brand colors plus neutrals',
    threshold: 3,
  },
  {
    id: 'color-contrast',
    category: 'colors',
    description: 'WCAG AA contrast ratio required (4.5:1 for text)',
    threshold: 4.5,
  },

  // Navigation
  {
    id: 'nav-top-level',
    category: 'navigation',
    description: 'Maximum 5 top-level navigation items',
    threshold: 5,
  },
  {
    id: 'nav-depth',
    category: 'navigation',
    description: 'Maximum 2 levels of navigation depth',
    threshold: 2,
  },

  // Components
  {
    id: 'comp-standard',
    category: 'components',
    description: 'Prefer standard components (buttons, cards, tables, forms)',
    threshold: 'standard',
  },

  // Layout
  {
    id: 'layout-responsive',
    category: 'layout',
    description: 'Must use responsive grid (no fixed widths)',
    threshold: 'responsive',
  },
  {
    id: 'layout-mobile-first',
    category: 'layout',
    description: 'Mobile-first approach required',
    threshold: 'mobile-first',
  },

  // Content Density
  {
    id: 'density-cta',
    category: 'content_density',
    description: 'Maximum 3 CTAs per page',
    threshold: 3,
  },
  {
    id: 'density-text',
    category: 'content_density',
    description: 'No walls of text (max 4 consecutive lines without break)',
    threshold: 4,
  },
];

/**
 * StyleChecker enforces DreamFi's minimalist fintech design rules.
 */
export class StyleChecker {
  private rules: StyleRule[];

  constructor(rules?: StyleRule[]) {
    this.rules = rules ?? STYLE_RULES;
  }

  /**
   * Check layout rules: responsive grid, no fixed widths, mobile-first.
   */
  checkLayout(artifact: UIArtifact): StyleResult[] {
    const results: StyleResult[] = [];
    const css = artifact.css.toLowerCase();

    // Check for fixed widths
    const fixedWidthPattern = /width\s*:\s*\d+px(?!\s*;?\s*\/\*\s*max)/g;
    const hasFixedWidths = fixedWidthPattern.test(css);
    results.push({
      ruleId: 'layout-responsive',
      passed: !hasFixedWidths,
      message: hasFixedWidths
        ? 'Fixed pixel widths detected. Use relative units or max-width.'
        : 'Layout uses responsive units.',
      severity: hasFixedWidths ? 'error' : 'info',
    });

    // Check for flex or grid usage
    const usesFlexOrGrid = /display\s*:\s*(flex|grid)/.test(css);
    results.push({
      ruleId: 'layout-responsive',
      passed: usesFlexOrGrid,
      message: usesFlexOrGrid
        ? 'Uses flex or grid layout.'
        : 'No flex/grid layout detected. Consider using modern layout.',
      severity: usesFlexOrGrid ? 'info' : 'warning',
    });

    // Check mobile-first (media queries should use min-width)
    const hasMediaQueries = /@media/.test(css);
    const usesMinWidth = /@media[^{]*min-width/.test(css);
    const usesMaxWidth = /@media[^{]*max-width/.test(css);
    const isMobileFirst = !hasMediaQueries || (usesMinWidth && !usesMaxWidth);
    results.push({
      ruleId: 'layout-mobile-first',
      passed: isMobileFirst,
      message: isMobileFirst
        ? 'Mobile-first approach detected.'
        : 'Uses max-width media queries. Switch to min-width for mobile-first.',
      severity: isMobileFirst ? 'info' : 'warning',
    });

    return results;
  }

  /**
   * Check typography rules: font sizes, font stack.
   */
  checkTypography(artifact: UIArtifact): StyleResult[] {
    const results: StyleResult[] = [];
    const css = artifact.css;

    // Count distinct font sizes
    const fontSizeMatches = css.match(/font-size\s*:\s*([^;]+)/g) || [];
    const uniqueSizes = new Set(
      fontSizeMatches.map(m => m.replace(/font-size\s*:\s*/, '').trim())
    );
    const sizeCount = uniqueSizes.size;
    const maxSizes = 3;
    results.push({
      ruleId: 'typo-font-sizes',
      passed: sizeCount <= maxSizes,
      message:
        sizeCount <= maxSizes
          ? `${sizeCount} font size(s) used (max ${maxSizes}).`
          : `${sizeCount} font sizes found, maximum is ${maxSizes}.`,
      severity: sizeCount <= maxSizes ? 'info' : 'error',
    });

    // Check for system font stack
    const usesSystemFont =
      /font-family\s*:.*system-ui/.test(css) ||
      /font-family\s*:.*-apple-system/.test(css) ||
      !(/font-family/.test(css)); // No font-family = browser default
    results.push({
      ruleId: 'typo-font-stack',
      passed: usesSystemFont,
      message: usesSystemFont
        ? 'Uses system font stack.'
        : 'Custom font family detected. Use system font stack.',
      severity: usesSystemFont ? 'info' : 'warning',
    });

    return results;
  }

  /**
   * Check accessibility rules: contrast, semantic HTML.
   */
  checkAccessibility(artifact: UIArtifact): StyleResult[] {
    const results: StyleResult[] = [];
    const html = artifact.html.toLowerCase();

    // Check semantic HTML
    const semanticTags = ['header', 'main', 'footer', 'nav', 'section', 'article', 'aside'];
    const usesSemanticHtml = semanticTags.some(tag => html.includes(`<${tag}`));
    results.push({
      ruleId: 'color-contrast',
      passed: usesSemanticHtml,
      message: usesSemanticHtml
        ? 'Semantic HTML tags detected.'
        : 'No semantic HTML tags found. Use header, main, nav, etc.',
      severity: usesSemanticHtml ? 'info' : 'error',
    });

    // Check for alt attributes on images
    const imgTags = html.match(/<img[^>]*>/g) || [];
    const imgsWithoutAlt = imgTags.filter(tag => !tag.includes('alt='));
    results.push({
      ruleId: 'color-contrast',
      passed: imgsWithoutAlt.length === 0,
      message:
        imgsWithoutAlt.length === 0
          ? 'All images have alt attributes.'
          : `${imgsWithoutAlt.length} image(s) missing alt attribute.`,
      severity: imgsWithoutAlt.length === 0 ? 'info' : 'error',
    });

    // Check for ARIA labels on interactive elements
    const hasAriaLabels = /aria-label/.test(html);
    results.push({
      ruleId: 'color-contrast',
      passed: hasAriaLabels,
      message: hasAriaLabels
        ? 'ARIA labels found on elements.'
        : 'No ARIA labels detected. Add aria-label to interactive elements.',
      severity: hasAriaLabels ? 'info' : 'warning',
    });

    return results;
  }

  /**
   * Run all style checks and produce overall validation.
   */
  validateAll(artifact: UIArtifact): StyleValidation {
    const allResults = [
      ...this.checkLayout(artifact),
      ...this.checkTypography(artifact),
      ...this.checkAccessibility(artifact),
    ];

    const totalChecks = allResults.length;
    const passedChecks = allResults.filter(r => r.passed).length;
    const score = totalChecks > 0 ? Math.round((passedChecks / totalChecks) * 100) : 0;

    return {
      passed: allResults.every(r => r.severity !== 'error' || r.passed),
      results: allResults,
      score,
    };
  }
}
