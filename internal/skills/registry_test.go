package skills

import "testing"

func TestRegistryShipsNineSkills(t *testing.T) {
	if len(Registry) != 9 {
		t.Fatalf("len(Registry) = %d, want 9", len(Registry))
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
