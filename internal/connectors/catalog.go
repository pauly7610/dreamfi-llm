package connectors

import "strings"

type ConnectionMethod string

const (
	ConnectionMethodOnyxNative      ConnectionMethod = "onyx_native"
	ConnectionMethodCustomIngestion ConnectionMethod = "custom_ingestion"
)

type ConnectorSpec struct {
	ConnectorID      string
	DisplayName      string
	Provider         string
	ConnectionMethod ConnectionMethod
	DocumentSetName  string
	DefaultEndpoints []string
	AuthHeader       string
	AuthScheme       string
}

var Catalog = []ConnectorSpec{
	{ConnectorID: "jira", DisplayName: "Jira", Provider: "jira", ConnectionMethod: ConnectionMethodOnyxNative, DocumentSetName: "dreamfi-source-jira"},
	{ConnectorID: "confluence", DisplayName: "Confluence", Provider: "confluence", ConnectionMethod: ConnectionMethodOnyxNative, DocumentSetName: "dreamfi-source-confluence"},
	{ConnectorID: "dragonboat", DisplayName: "Dragonboat", Provider: "dragonboat", ConnectionMethod: ConnectionMethodCustomIngestion, DocumentSetName: "dreamfi-source-dragonboat", DefaultEndpoints: []string{"/api/v1/initiatives", "/api/v1/features"}, AuthHeader: "authorization", AuthScheme: "Bearer"},
	{ConnectorID: "metabase", DisplayName: "Metabase", Provider: "metabase", ConnectionMethod: ConnectionMethodCustomIngestion, DocumentSetName: "dreamfi-source-metabase", DefaultEndpoints: []string{"/api/card", "/api/dashboard"}, AuthHeader: "x-api-key"},
	{ConnectorID: "posthog", DisplayName: "PostHog", Provider: "posthog", ConnectionMethod: ConnectionMethodCustomIngestion, DocumentSetName: "dreamfi-source-posthog", DefaultEndpoints: []string{"/api/projects/{project_id}/insights", "/api/projects/{project_id}/dashboards"}, AuthHeader: "authorization", AuthScheme: "Bearer"},
	{ConnectorID: "ga", DisplayName: "Google Analytics", Provider: "ga4", ConnectionMethod: ConnectionMethodCustomIngestion, DocumentSetName: "dreamfi-source-ga", DefaultEndpoints: []string{"/v1beta/properties/{property_id}:runReport"}, AuthHeader: "authorization", AuthScheme: "Bearer"},
	{ConnectorID: "klaviyo", DisplayName: "Klaviyo", Provider: "klaviyo", ConnectionMethod: ConnectionMethodCustomIngestion, DocumentSetName: "dreamfi-source-klaviyo", DefaultEndpoints: []string{"/api/campaigns", "/api/flows", "/api/segments"}, AuthHeader: "authorization", AuthScheme: "Klaviyo-API-Key"},
	{ConnectorID: "netxd", DisplayName: "NetXD", Provider: "netxd", ConnectionMethod: ConnectionMethodCustomIngestion, DocumentSetName: "dreamfi-source-netxd", DefaultEndpoints: []string{"/api/payments", "/api/accounts"}, AuthHeader: "authorization", AuthScheme: "Bearer"},
	{ConnectorID: "sardine", DisplayName: "Sardine", Provider: "sardine", ConnectionMethod: ConnectionMethodCustomIngestion, DocumentSetName: "dreamfi-source-sardine", DefaultEndpoints: []string{"/api/v1/entities", "/api/v1/transactions"}, AuthHeader: "authorization", AuthScheme: "Bearer"},
	{ConnectorID: "socure", DisplayName: "Socure", Provider: "socure", ConnectionMethod: ConnectionMethodCustomIngestion, DocumentSetName: "dreamfi-source-socure", DefaultEndpoints: []string{"/api/decisions", "/api/documents"}, AuthHeader: "authorization", AuthScheme: "Bearer"},
}

func ByID(connectorID string) (ConnectorSpec, bool) {
	for _, connector := range Catalog {
		if connector.ConnectorID == connectorID {
			return connector, true
		}
	}
	return ConnectorSpec{}, false
}

func CustomConnectorIDs() []string {
	ids := make([]string, 0)
	for _, connector := range Catalog {
		if connector.ConnectionMethod == ConnectionMethodCustomIngestion {
			ids = append(ids, connector.ConnectorID)
		}
	}
	return ids
}

func DocumentSetAliases(connector ConnectorSpec) map[string]struct{} {
	aliases := map[string]struct{}{
		normalizeDocumentSetName(connector.DocumentSetName):                 {},
		normalizeDocumentSetName("dreamfi-source-" + connector.ConnectorID): {},
		normalizeDocumentSetName("dreamfi-" + connector.ConnectorID):        {},
		normalizeDocumentSetName("dreamfi-" + connector.DisplayName):        {},
	}
	return aliases
}

func normalizeDocumentSetName(value string) string {
	return strings.Join(strings.Fields(strings.ToLower(strings.ReplaceAll(value, "_", "-"))), "-")
}
