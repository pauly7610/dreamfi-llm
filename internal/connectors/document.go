package connectors

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"time"
)

type SourceDocument struct {
	ConnectorID string
	ExternalID  string
	Title       string
	BodyText    string
	SourceURL   string
	UpdatedAt   time.Time
	Metadata    map[string]any
}

func (d SourceDocument) ContentHash() string {
	raw, _ := json.Marshal([]any{d.ConnectorID, d.ExternalID, d.Title, d.BodyText, d.SourceURL, d.UpdatedAt.UTC().Format(time.RFC3339), d.Metadata})
	sum := sha256.Sum256(raw)
	return hex.EncodeToString(sum[:])
}

func (d SourceDocument) OnyxDocumentID() string {
	sum := sha256.Sum256([]byte(d.ConnectorID + ":" + d.ExternalID))
	return "dreamfi:" + d.ConnectorID + ":" + hex.EncodeToString(sum[:12])
}

func (d SourceDocument) OnyxMetadata() map[string]any {
	metadata := map[string]any{}
	for key, value := range d.Metadata {
		metadata[key] = value
	}
	metadata["dreamfi_scope"] = map[string]any{
		"source_ids": []string{d.ConnectorID},
	}
	return metadata
}
