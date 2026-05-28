package connectors

import "testing"

func TestAllCustomConnectorsHaveAdapters(t *testing.T) {
	for _, connectorID := range CustomConnectorIDs() {
		if _, ok := AdapterFor(connectorID); !ok {
			t.Fatalf("custom connector %q has no adapter", connectorID)
		}
	}
}

func TestDocumentSetAliasesIncludeExpectedDreamFiNames(t *testing.T) {
	connector, ok := ByID("metabase")
	if !ok {
		t.Fatal("metabase connector missing")
	}
	aliases := DocumentSetAliases(connector)
	for _, expected := range []string{"dreamfi-source-metabase", "dreamfi-metabase"} {
		if _, ok := aliases[expected]; !ok {
			t.Fatalf("alias %q missing from %#v", expected, aliases)
		}
	}
}
