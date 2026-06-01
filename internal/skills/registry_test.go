package skills

import "testing"

func TestRegistryShipsActiveSkillsOnly(t *testing.T) {
	if len(Registry) != 3 {
		t.Fatalf("len(Registry) = %d, want 3", len(Registry))
	}
	if _, ok := ByID("landing_page_copy"); ok {
		t.Fatal("archived landing_page_copy should not be in active registry")
	}
	if len(ArchivedRegistry) != 6 {
		t.Fatalf("len(ArchivedRegistry) = %d, want 6", len(ArchivedRegistry))
	}
}

func TestRegistryIncludesSupportAgent(t *testing.T) {
	spec, ok := ByID("support_agent")
	if !ok {
		t.Fatal("support_agent missing")
	}
	if spec.RunnerClass != "SupportAgentEval" {
		t.Fatalf("runner class = %q", spec.RunnerClass)
	}
}

func TestRegistryIDsAreUnique(t *testing.T) {
	seen := map[string]struct{}{}
	for _, spec := range Registry {
		if spec.SkillID == "" || spec.EvalTemplatePath == "" || spec.EvalRunnerPath == "" {
			t.Fatalf("incomplete spec = %#v", spec)
		}
		if _, ok := seen[spec.SkillID]; ok {
			t.Fatalf("duplicate skill id %q", spec.SkillID)
		}
		seen[spec.SkillID] = struct{}{}
	}
}
