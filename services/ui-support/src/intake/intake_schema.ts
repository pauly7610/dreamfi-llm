/**
 * UI Project Intake Schema
 *
 * Defines the intake request structure for UI projects, validates requests,
 * classifies artifact types, and maps target surfaces to skill evaluators.
 */

export interface UIIntakeRequest {
  title: string;
  requestedBy: string;
  scope: string;
  userStories: string[];
  acceptanceCriteria: string[];
  designRefs: string[]; // Figma URLs
  targetSurfaces: TargetSurface[];
  priority: 'P0' | 'P1' | 'P2' | 'P3';
  deadline: string; // ISO date
}

export type TargetSurface =
  | 'landing'
  | 'support'
  | 'internal'
  | 'email'
  | 'product';

export type ArtifactType = 'spec' | 'epic' | 'flow' | 'copy' | 'prototype';

export type SkillName =
  | 'landing_page_copy'
  | 'support_agent'
  | 'meeting_summary'
  | 'newsletter_headline'
  | 'product_description'
  | 'cold_email';

export interface ValidationResult {
  valid: boolean;
  errors: string[];
}

const REQUIRED_FIELDS: (keyof UIIntakeRequest)[] = [
  'title',
  'requestedBy',
  'scope',
  'userStories',
  'acceptanceCriteria',
  'targetSurfaces',
  'priority',
  'deadline',
];

const SURFACE_TO_SKILL: Record<TargetSurface, SkillName> = {
  landing: 'landing_page_copy',
  support: 'support_agent',
  internal: 'meeting_summary',
  email: 'newsletter_headline',
  product: 'product_description',
};

/**
 * Validates a UI intake request for completeness and correctness.
 */
export function validateIntake(request: UIIntakeRequest): ValidationResult {
  const errors: string[] = [];

  for (const field of REQUIRED_FIELDS) {
    const value = request[field];
    if (value === undefined || value === null) {
      errors.push(`Missing required field: ${field}`);
    } else if (Array.isArray(value) && value.length === 0) {
      errors.push(`Field '${field}' must have at least one entry`);
    } else if (typeof value === 'string' && value.trim() === '') {
      errors.push(`Field '${field}' must not be empty`);
    }
  }

  if (request.designRefs) {
    for (const ref of request.designRefs) {
      if (!ref.startsWith('https://www.figma.com/') && !ref.startsWith('https://figma.com/')) {
        errors.push(`Invalid Figma URL: ${ref}`);
      }
    }
  }

  if (request.targetSurfaces) {
    const validSurfaces: TargetSurface[] = ['landing', 'support', 'internal', 'email', 'product'];
    for (const surface of request.targetSurfaces) {
      if (!validSurfaces.includes(surface)) {
        errors.push(`Invalid target surface: ${surface}`);
      }
    }
  }

  if (request.deadline) {
    const deadlineDate = new Date(request.deadline);
    if (isNaN(deadlineDate.getTime())) {
      errors.push(`Invalid deadline date: ${request.deadline}`);
    }
  }

  return { valid: errors.length === 0, errors };
}

/**
 * Classifies the type of artifact to produce from an intake request.
 */
export function classifyArtifactType(request: UIIntakeRequest): ArtifactType {
  if (request.userStories.length > 3 && request.acceptanceCriteria.length > 5) {
    return 'epic';
  }
  if (request.designRefs && request.designRefs.length > 0) {
    return 'prototype';
  }
  if (request.targetSurfaces.some(s => ['landing', 'email', 'product'].includes(s))) {
    return 'copy';
  }
  if (request.targetSurfaces.includes('internal')) {
    return 'flow';
  }
  return 'spec';
}

/**
 * Maps a target surface to the appropriate skill evaluator.
 */
export function mapToSkill(targetSurface: TargetSurface): SkillName {
  const skill = SURFACE_TO_SKILL[targetSurface];
  if (!skill) {
    throw new Error(`No skill mapping for surface: ${targetSurface}`);
  }
  return skill;
}
