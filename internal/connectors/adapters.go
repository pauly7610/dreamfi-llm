package connectors

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strconv"
	"strings"
	"time"
)

type Adapter interface {
	FetchDocuments(ctx context.Context, connector ConnectorSpec, config map[string]string, secret string, limit int) ([]SourceDocument, error)
}

var Adapters = map[string]Adapter{
	"dragonboat": RestAdapter{},
	"metabase":   RestAdapter{},
	"posthog":    RestAdapter{},
	"klaviyo":    RestAdapter{},
	"netxd":      RestAdapter{},
	"sardine":    RestAdapter{},
	"socure":     RestAdapter{},
	"ga":         GoogleAnalyticsAdapter{},
}

type RestAdapter struct {
	Client *http.Client
}

func (a RestAdapter) FetchDocuments(ctx context.Context, connector ConnectorSpec, config map[string]string, secret string, limit int) ([]SourceDocument, error) {
	baseURL := strings.TrimRight(config["base_url"], "/")
	if baseURL == "" {
		return nil, errors.New("base_url is required")
	}
	client := a.Client
	if client == nil {
		client = http.DefaultClient
	}
	paths := configuredPaths(config["endpoints"], connector.DefaultEndpoints)
	documents := make([]SourceDocument, 0)
	for _, path := range paths {
		if limit > 0 && len(documents) >= limit {
			break
		}
		req, err := http.NewRequestWithContext(ctx, http.MethodGet, joinURL(baseURL, expandPath(path, config)), nil)
		if err != nil {
			return nil, err
		}
		applyAuth(req, connector, config, secret)
		resp, err := client.Do(req)
		if err != nil {
			return nil, err
		}
		raw, readErr := io.ReadAll(resp.Body)
		resp.Body.Close()
		if readErr != nil {
			return nil, readErr
		}
		if resp.StatusCode >= 400 {
			return nil, fmt.Errorf("%s returned %d", req.URL.String(), resp.StatusCode)
		}
		items, err := decodeItems(raw)
		if err != nil {
			return nil, err
		}
		for index, item := range items {
			if limit > 0 && len(documents) >= limit {
				break
			}
			documents = append(documents, documentFromItem(connector, baseURL, path, index, item, config))
		}
	}
	return documents, nil
}

type GoogleAnalyticsAdapter struct {
	Client *http.Client
}

func (a GoogleAnalyticsAdapter) FetchDocuments(ctx context.Context, connector ConnectorSpec, config map[string]string, secret string, limit int) ([]SourceDocument, error) {
	baseURL := strings.TrimRight(config["base_url"], "/")
	if baseURL == "" {
		baseURL = "https://analyticsdata.googleapis.com"
	}
	propertyID := config["property_id"]
	if propertyID == "" {
		return nil, errors.New("property_id is required")
	}
	client := a.Client
	if client == nil {
		client = http.DefaultClient
	}
	body := map[string]any{
		"dateRanges": []map[string]string{{
			"startDate": defaultString(config["start_date"], "7daysAgo"),
			"endDate":   defaultString(config["end_date"], "today"),
		}},
		"dimensions": namedRows(csvValues(config["dimensions"], []string{"country"})),
		"metrics":    namedRows(csvValues(config["metrics"], []string{"sessions"})),
	}
	rawBody, _ := json.Marshal(body)
	req, err := http.NewRequestWithContext(
		ctx,
		http.MethodPost,
		joinURL(baseURL, "/v1beta/properties/"+url.PathEscape(propertyID)+":runReport"),
		strings.NewReader(string(rawBody)),
	)
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/json")
	applyAuth(req, connector, config, secret)
	resp, err := client.Do(req)
	if err != nil {
		return nil, err
	}
	raw, readErr := io.ReadAll(resp.Body)
	resp.Body.Close()
	if readErr != nil {
		return nil, readErr
	}
	if resp.StatusCode >= 400 {
		return nil, fmt.Errorf("%s returned %d", req.URL.String(), resp.StatusCode)
	}
	var payload struct {
		Rows []map[string]any `json:"rows"`
	}
	if err := json.Unmarshal(raw, &payload); err != nil {
		return nil, err
	}
	documents := make([]SourceDocument, 0, len(payload.Rows))
	for index, row := range payload.Rows {
		if limit > 0 && len(documents) >= limit {
			break
		}
		documents = append(documents, SourceDocument{
			ConnectorID: connector.ConnectorID,
			ExternalID:  "ga-row-" + strconv.Itoa(index),
			Title:       "Google Analytics report row " + strconv.Itoa(index+1),
			BodyText:    compactJSON(row),
			UpdatedAt:   time.Now().UTC(),
			Metadata:    configuredMetadata(config),
		})
	}
	return documents, nil
}

func AdapterFor(connectorID string) (Adapter, bool) {
	adapter, ok := Adapters[connectorID]
	return adapter, ok
}

func applyAuth(req *http.Request, connector ConnectorSpec, config map[string]string, secret string) {
	if secret == "" {
		return
	}
	header := defaultString(config["auth_header"], connector.AuthHeader)
	if header == "" {
		header = "authorization"
	}
	scheme := defaultString(config["auth_scheme"], connector.AuthScheme)
	value := secret
	if scheme != "" {
		value = scheme + " " + secret
	}
	req.Header.Set(header, value)
}

func configuredPaths(value string, defaults []string) []string {
	if strings.TrimSpace(value) == "" {
		return defaults
	}
	return csvValues(value, defaults)
}

func csvValues(value string, defaults []string) []string {
	if strings.TrimSpace(value) == "" {
		return defaults
	}
	parts := strings.Split(value, ",")
	values := make([]string, 0, len(parts))
	for _, part := range parts {
		if trimmed := strings.TrimSpace(part); trimmed != "" {
			values = append(values, trimmed)
		}
	}
	if len(values) == 0 {
		return defaults
	}
	return values
}

func namedRows(values []string) []map[string]string {
	rows := make([]map[string]string, 0, len(values))
	for _, value := range values {
		rows = append(rows, map[string]string{"name": value})
	}
	return rows
}

func decodeItems(raw []byte) ([]map[string]any, error) {
	var array []map[string]any
	if err := json.Unmarshal(raw, &array); err == nil {
		return array, nil
	}
	var envelope map[string]any
	if err := json.Unmarshal(raw, &envelope); err != nil {
		return nil, err
	}
	for _, key := range []string{"items", "data", "results", "cards", "dashboards"} {
		if rawItems, ok := envelope[key].([]any); ok {
			items := make([]map[string]any, 0, len(rawItems))
			for _, rawItem := range rawItems {
				if item, ok := rawItem.(map[string]any); ok {
					items = append(items, item)
				}
			}
			return items, nil
		}
	}
	return []map[string]any{envelope}, nil
}

func documentFromItem(connector ConnectorSpec, baseURL string, path string, index int, item map[string]any, config map[string]string) SourceDocument {
	title := firstText(item, "name", "title", "display_name", "subject")
	if title == "" {
		title = connector.DisplayName + " item " + strconv.Itoa(index+1)
	}
	externalID := firstText(item, "id", "uuid", "key", "slug")
	if externalID == "" {
		externalID = strings.Trim(path, "/") + ":" + strconv.Itoa(index)
	}
	updatedAt := parseTime(firstText(item, "updated_at", "updatedAt", "last_modified", "created_at"))
	sourceURL := firstText(item, "url", "link", "source_url")
	if sourceURL == "" && firstText(item, "id") != "" {
		sourceURL = joinURL(baseURL, strings.TrimSuffix(path, "s")+"/"+url.PathEscape(firstText(item, "id")))
	}
	body := firstText(item, "description", "summary", "body", "text")
	if body == "" {
		body = compactJSON(item)
	}
	return SourceDocument{
		ConnectorID: connector.ConnectorID,
		ExternalID:  externalID,
		Title:       title,
		BodyText:    body,
		SourceURL:   sourceURL,
		UpdatedAt:   updatedAt,
		Metadata:    configuredMetadata(config),
	}
}

func configuredMetadata(config map[string]string) map[string]any {
	metadata := map[string]any{}
	for _, key := range []string{"product_area", "owner"} {
		if config[key] != "" {
			metadata[key] = config[key]
		}
	}
	if config["topic_ids"] != "" {
		metadata["topic_ids"] = csvValues(config["topic_ids"], nil)
	}
	return metadata
}

func expandPath(path string, config map[string]string) string {
	for key, value := range config {
		path = strings.ReplaceAll(path, "{"+key+"}", url.PathEscape(value))
	}
	return path
}

func joinURL(baseURL string, path string) string {
	if strings.HasPrefix(path, "http://") || strings.HasPrefix(path, "https://") {
		return path
	}
	if !strings.HasPrefix(path, "/") {
		path = "/" + path
	}
	return strings.TrimRight(baseURL, "/") + path
}

func firstText(item map[string]any, keys ...string) string {
	for _, key := range keys {
		if value, ok := item[key]; ok && value != nil {
			return fmt.Sprint(value)
		}
	}
	return ""
}

func parseTime(value string) time.Time {
	if value == "" {
		return time.Now().UTC()
	}
	for _, layout := range []string{time.RFC3339Nano, time.RFC3339, "2006-01-02"} {
		parsed, err := time.Parse(layout, value)
		if err == nil {
			return parsed.UTC()
		}
	}
	return time.Now().UTC()
}

func compactJSON(value any) string {
	raw, err := json.Marshal(value)
	if err != nil {
		return fmt.Sprint(value)
	}
	return string(raw)
}

func defaultString(value string, fallback string) string {
	if value != "" {
		return value
	}
	return fallback
}
