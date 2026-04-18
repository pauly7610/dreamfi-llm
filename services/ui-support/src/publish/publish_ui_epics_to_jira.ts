/**
 * Publish UI Epics to Jira
 *
 * Creates epics and stories in Jira from UI intake requests,
 * applies taxonomy rules from Phase 3, and links to Dragonboat features.
 */

export interface EpicData {
  title: string;
  description: string;
  stories: StoryData[];
  acceptanceCriteria: string[];
  priority: 'P0' | 'P1' | 'P2' | 'P3';
  labels: string[];
  dragonboatFeatureId?: string;
}

export interface StoryData {
  title: string;
  description: string;
  acceptanceCriteria: string[];
  storyPoints?: number;
  assignee?: string;
}

export interface JiraIssueResult {
  issueKey: string;
  issueId: string;
  url: string;
}

interface JiraClient {
  createIssue(payload: Record<string, unknown>): Promise<{ key: string; id: string; self: string }>;
  addLink(issueKey: string, linkType: string, url: string): Promise<void>;
}

const PRIORITY_MAP: Record<string, string> = {
  P0: 'Highest',
  P1: 'High',
  P2: 'Medium',
  P3: 'Low',
};

const TAXONOMY_LABELS = ['ui-support', 'dreamfi'];

/**
 * Publishes UI epics and their stories to Jira.
 */
export async function publishUIEpics(
  epicData: EpicData,
  projectKey: string,
  client?: JiraClient
): Promise<string[]> {
  if (!client) {
    throw new Error('Jira client not configured');
  }

  const issueKeys: string[] = [];

  // Create the epic
  const epicPayload = {
    fields: {
      project: { key: projectKey },
      summary: epicData.title,
      description: formatDescription(epicData.description, epicData.acceptanceCriteria),
      issuetype: { name: 'Epic' },
      priority: { name: PRIORITY_MAP[epicData.priority] || 'Medium' },
      labels: [...TAXONOMY_LABELS, ...epicData.labels],
      customfield_10011: epicData.title, // Epic Name
    },
  };

  const epicResult = await client.createIssue(epicPayload);
  issueKeys.push(epicResult.key);

  // Link to Dragonboat if feature ID provided
  if (epicData.dragonboatFeatureId) {
    await client.addLink(
      epicResult.key,
      'relates to',
      `https://app.dragonboat.io/features/${epicData.dragonboatFeatureId}`
    );
  }

  // Create stories under the epic
  for (const story of epicData.stories) {
    const storyPayload = {
      fields: {
        project: { key: projectKey },
        summary: story.title,
        description: formatDescription(story.description, story.acceptanceCriteria),
        issuetype: { name: 'Story' },
        labels: TAXONOMY_LABELS,
        parent: { key: epicResult.key },
        ...(story.storyPoints && { customfield_10016: story.storyPoints }),
        ...(story.assignee && { assignee: { name: story.assignee } }),
      },
    };

    const storyResult = await client.createIssue(storyPayload);
    issueKeys.push(storyResult.key);
  }

  return issueKeys;
}

function formatDescription(description: string, criteria: string[]): string {
  let formatted = description;
  if (criteria.length > 0) {
    formatted += '\n\nh3. Acceptance Criteria\n';
    for (const c of criteria) {
      formatted += `* ${c}\n`;
    }
  }
  return formatted;
}
