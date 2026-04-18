/**
 * Link Lucid Flow
 *
 * Creates bidirectional links between UI artifacts and Lucid flow diagrams.
 * Updates the Confluence spec page with a flow embed.
 */

export interface LucidLinkResult {
  linkUrl: string;
  artifactId: string;
  lucidDocumentId: string;
  confluencePageUpdated: boolean;
}

interface LucidClient {
  getDocumentUrl(documentId: string): Promise<string>;
  addExternalLink(documentId: string, url: string, label: string): Promise<void>;
}

interface ConfluenceClient {
  getPageContent(pageId: string): Promise<{ body: string; version: number }>;
  updatePage(
    pageId: string,
    body: string,
    version: number
  ): Promise<void>;
}

interface ArtifactStore {
  getArtifact(artifactId: string): Promise<{
    id: string;
    confluencePageId?: string;
    url: string;
  }>;
  updateArtifact(artifactId: string, data: Record<string, unknown>): Promise<void>;
}

/**
 * Creates a bidirectional link between a UI artifact and a Lucid flow diagram.
 * Also updates the associated Confluence spec page with the flow embed.
 */
export async function linkLucidFlow(
  artifactId: string,
  lucidDocumentId: string,
  lucidClient?: LucidClient,
  confluenceClient?: ConfluenceClient,
  artifactStore?: ArtifactStore
): Promise<string> {
  if (!lucidClient || !artifactStore) {
    throw new Error('Lucid client and artifact store must be configured');
  }

  // Get the Lucid document URL
  const lucidUrl = await lucidClient.getDocumentUrl(lucidDocumentId);

  // Get the artifact details
  const artifact = await artifactStore.getArtifact(artifactId);

  // Create link from Lucid back to the artifact
  await lucidClient.addExternalLink(
    lucidDocumentId,
    artifact.url,
    `UI Artifact: ${artifactId}`
  );

  // Update artifact with Lucid reference
  await artifactStore.updateArtifact(artifactId, {
    lucidDocumentId,
    lucidUrl,
  });

  // Update Confluence page if linked
  let confluenceUpdated = false;
  if (artifact.confluencePageId && confluenceClient) {
    const page = await confluenceClient.getPageContent(artifact.confluencePageId);
    const flowEmbed = buildFlowEmbed(lucidUrl, lucidDocumentId);
    const updatedBody = insertFlowSection(page.body, flowEmbed);
    await confluenceClient.updatePage(
      artifact.confluencePageId,
      updatedBody,
      page.version + 1
    );
    confluenceUpdated = true;
  }

  return lucidUrl;
}

function buildFlowEmbed(lucidUrl: string, documentId: string): string {
  return [
    '<h2>Flow Diagram</h2>',
    `<p><a href="${lucidUrl}">View in Lucidchart (${documentId})</a></p>`,
    `<ac:structured-macro ac:name="iframe">`,
    `  <ac:parameter ac:name="src">${lucidUrl}/embed</ac:parameter>`,
    `  <ac:parameter ac:name="width">100%</ac:parameter>`,
    `  <ac:parameter ac:name="height">600</ac:parameter>`,
    `</ac:structured-macro>`,
  ].join('\n');
}

function insertFlowSection(existingBody: string, flowEmbed: string): string {
  // Replace existing flow section or append
  const flowSectionRegex = /<h2>Flow Diagram<\/h2>[\s\S]*?(?=<h2>|$)/;
  if (flowSectionRegex.test(existingBody)) {
    return existingBody.replace(flowSectionRegex, flowEmbed);
  }
  return existingBody + '\n' + flowEmbed;
}
