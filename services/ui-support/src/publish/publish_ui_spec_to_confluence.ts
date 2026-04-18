/**
 * Publish UI Spec to Confluence
 *
 * Formats and publishes UI specifications to Confluence, including
 * style rules summary, acceptance criteria, skill mapping, and
 * links to Figma designs and Lucid flows.
 */

export interface UISpec {
  title: string;
  summary: string;
  acceptanceCriteria: string[];
  styleRulesSummary: string;
  skillMapping: string;
  figmaUrls: string[];
  lucidFlowUrls: string[];
  content: string;
  metadata: Record<string, unknown>;
}

export interface ConfluencePageResult {
  pageUrl: string;
  pageId: string;
  version: number;
}

interface ConfluenceClient {
  createPage(
    spaceKey: string,
    title: string,
    body: string,
    parentPageId?: string
  ): Promise<{ id: string; _links: { webui: string }; version: { number: number } }>;
}

/**
 * Publishes a UI spec to Confluence with full formatting.
 */
export async function publishUISpec(
  spec: UISpec,
  spaceKey: string,
  parentPageId?: string,
  client?: ConfluenceClient
): Promise<string> {
  const body = formatSpecForConfluence(spec);

  if (!client) {
    throw new Error('Confluence client not configured');
  }

  const result = await client.createPage(spaceKey, spec.title, body, parentPageId);
  return result._links.webui;
}

function formatSpecForConfluence(spec: UISpec): string {
  const sections: string[] = [];

  sections.push(`<h1>${escapeHtml(spec.title)}</h1>`);
  sections.push(`<p>${escapeHtml(spec.summary)}</p>`);

  // Style Rules Summary
  sections.push('<h2>Style Rules</h2>');
  sections.push(`<p>${escapeHtml(spec.styleRulesSummary)}</p>`);

  // Acceptance Criteria
  sections.push('<h2>Acceptance Criteria</h2>');
  sections.push('<ul>');
  for (const criterion of spec.acceptanceCriteria) {
    sections.push(`<li>${escapeHtml(criterion)}</li>`);
  }
  sections.push('</ul>');

  // Skill Mapping
  sections.push('<h2>Skill Mapping</h2>');
  sections.push(`<p>${escapeHtml(spec.skillMapping)}</p>`);

  // Figma Designs
  if (spec.figmaUrls.length > 0) {
    sections.push('<h2>Design References</h2>');
    sections.push('<ul>');
    for (const url of spec.figmaUrls) {
      sections.push(`<li><a href="${escapeHtml(url)}">${escapeHtml(url)}</a></li>`);
    }
    sections.push('</ul>');
  }

  // Lucid Flows
  if (spec.lucidFlowUrls.length > 0) {
    sections.push('<h2>Flow Diagrams</h2>');
    sections.push('<ul>');
    for (const url of spec.lucidFlowUrls) {
      sections.push(`<li><a href="${escapeHtml(url)}">${escapeHtml(url)}</a></li>`);
    }
    sections.push('</ul>');
  }

  // Main Content
  sections.push('<h2>Specification</h2>');
  sections.push(`<div>${escapeHtml(spec.content)}</div>`);

  return sections.join('\n');
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
