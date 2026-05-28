package skills

type SkillSpec struct {
	SkillID          string
	DisplayName      string
	Description      string
	EvalTemplatePath string
	EvalRunnerPath   string
	RunnerModule     string
	RunnerClass      string
}

var Registry = []SkillSpec{
	{"meeting_summary", "Meeting Summary", "Generates meeting summaries with decisions, action items, open questions.", "evals/meeting-summary.md", "evals/runners/run_meeting_summary_eval.py", "evals.runners.run_meeting_summary_eval", "MeetingSummaryEval"},
	{"cold_email", "Cold Email", "Generates short, specific cold outreach emails.", "evals/cold-email.md", "evals/runners/run_cold_email_eval.py", "evals.runners.run_cold_email_eval", "ColdEmailEval"},
	{"landing_page_copy", "Landing Page Copy", "Generates landing page hero + body copy.", "evals/landing-page-copy.md", "evals/runners/run_landing_page_eval.py", "evals.runners.run_landing_page_eval", "LandingPageCopyEval"},
	{"newsletter_headline", "Newsletter Headline", "Generates newsletter headlines with a specific hook.", "evals/newsletter-headline.md", "evals/runners/run_newsletter_headline_eval.py", "evals.runners.run_newsletter_headline_eval", "NewsletterHeadlineEval"},
	{"product_description", "Product Description", "Generates product descriptions with benefit + spec.", "evals/product-description.md", "evals/runners/run_product_description_eval.py", "evals.runners.run_product_description_eval", "ProductDescriptionEval"},
	{"resume_bullet", "Resume Bullet", "Generates resume bullets with metric + outcome.", "evals/resume-bullet.md", "evals/runners/run_resume_bullet_eval.py", "evals.runners.run_resume_bullet_eval", "ResumeBulletEval"},
	{"short_form_script", "Short-form Script", "Generates short-form video scripts with hook + CTA.", "evals/short-form-script.md", "evals/runners/run_short_form_script_eval.py", "evals.runners.run_short_form_script_eval", "ShortFormScriptEval"},
	{"agent_system_prompt", "Agent System Prompt", "Generates robust agent system prompts.", "evals/agent-system-prompt.md", "evals/runners/run_agent_system_prompt_eval.py", "evals.runners.run_agent_system_prompt_eval", "AgentSystemPromptEval"},
	{"support_agent", "Support Agent", "Generates support-agent replies with empathy + resolution.", "evals/support-agent.md", "evals/runners/run_support_agent_eval.py", "evals.runners.run_support_agent_eval", "SupportAgentEval"},
}

func ByID(skillID string) (SkillSpec, bool) {
	for _, spec := range Registry {
		if spec.SkillID == skillID {
			return spec, true
		}
	}
	return SkillSpec{}, false
}
