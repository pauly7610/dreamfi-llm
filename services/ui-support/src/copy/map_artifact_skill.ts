/**
 * Map Artifact to Skill
 *
 * Maps UI artifacts to their appropriate skill for copy evaluation.
 * Every artifact must map to exactly ONE skill (enforced).
 */

export type ArtifactSurface =
  | 'landing'
  | 'support'
  | 'internal-update'
  | 'release-summary'
  | 'email'
  | 'outreach';

export type SkillName =
  | 'landing_page_copy'
  | 'support_agent'
  | 'meeting_summary'
  | 'product_description'
  | 'newsletter_headline'
  | 'cold_email';

export interface SkillMapping {
  skillName: SkillName;
  constraints: SkillConstraints;
  template: string;
}

export interface SkillConstraints {
  maxWords?: number;
  minWords?: number;
  requiredElements: string[];
  bannedPatterns: string[];
}

export interface MappingValidation {
  valid: boolean;
  reason: string;
}

export interface Artifact {
  id: string;
  surface: ArtifactSurface;
  content: string;
  metadata: Record<string, unknown>;
}

/**
 * Surface-to-skill mapping table. Each surface maps to exactly one skill.
 */
export const SURFACE_SKILL_MAP: Record<ArtifactSurface, SkillName> = {
  'landing': 'landing_page_copy',
  'support': 'support_agent',
  'internal-update': 'meeting_summary',
  'release-summary': 'product_description',
  'email': 'newsletter_headline',
  'outreach': 'cold_email',
};

const SKILL_CONSTRAINTS: Record<SkillName, SkillConstraints> = {
  landing_page_copy: {
    minWords: 80,
    maxWords: 150,
    requiredElements: ['headline', 'subheadline', 'cta'],
    bannedPatterns: [
      'revolutionary', 'cutting-edge', 'synergy', 'next-level',
      'game-changing', 'leverage', 'unlock', 'transform',
      'streamline', 'empower', 'innovative', 'seamless',
      'robust', 'scalable', 'holistic',
    ],
  },
  support_agent: {
    maxWords: 120,
    requiredElements: ['resolution_steps', 'escalation_path'],
    bannedPatterns: [],
  },
  meeting_summary: {
    maxWords: 300,
    requiredElements: ['decisions', 'action_items', 'open_questions'],
    bannedPatterns: [],
  },
  product_description: {
    minWords: 100,
    maxWords: 200,
    requiredElements: ['problem_statement', 'customer_result', 'objection_handler'],
    bannedPatterns: ['unlike', 'compared to', 'better than'],
  },
  newsletter_headline: {
    maxWords: 10,
    requiredElements: ['number', 'curiosity_gap'],
    bannedPatterns: [],
  },
  cold_email: {
    maxWords: 75,
    requiredElements: ['prospect_reference', 'specific_number', 'closing_question'],
    bannedPatterns: [],
  },
};

const SKILL_TEMPLATES: Record<SkillName, string> = {
  landing_page_copy: '[Headline with number]\n[Pain point sentence]\n[Value proposition]\n[CTA with action verb]',
  support_agent: '[Acknowledge issue]\n[Resolution steps]\n[Escalation if needed]',
  meeting_summary: '## Decisions\n\n## Action Items\n\n## Open Questions',
  product_description: '[Problem statement]\n[Product solution]\n[Customer result]\n[Objection handler]',
  newsletter_headline: '[Subject: Number + curiosity gap]\n[Preview: New info]',
  cold_email: '[Specific result with number]\n[Prospect-specific reference]\n[Concrete question]',
};

/**
 * Maps an artifact to its appropriate skill for copy evaluation.
 * Every artifact maps to exactly ONE skill.
 */
export function mapArtifactToSkill(artifact: Artifact): SkillMapping {
  const skillName = SURFACE_SKILL_MAP[artifact.surface];
  if (!skillName) {
    throw new Error(
      `No skill mapping for surface '${artifact.surface}'. ` +
      `Valid surfaces: ${Object.keys(SURFACE_SKILL_MAP).join(', ')}`
    );
  }

  return {
    skillName,
    constraints: SKILL_CONSTRAINTS[skillName],
    template: SKILL_TEMPLATES[skillName],
  };
}

/**
 * Validates that a mapping between artifact and skill is correct.
 */
export function validateMapping(
  artifact: Artifact,
  skillName: SkillName
): MappingValidation {
  const expectedSkill = SURFACE_SKILL_MAP[artifact.surface];

  if (!expectedSkill) {
    return {
      valid: false,
      reason: `Unknown surface '${artifact.surface}'.`,
    };
  }

  if (expectedSkill !== skillName) {
    return {
      valid: false,
      reason:
        `Surface '${artifact.surface}' should map to '${expectedSkill}', ` +
        `not '${skillName}'.`,
    };
  }

  return { valid: true, reason: 'Mapping is correct.' };
}
