package onyx

import (
	"bytes"
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

const defaultTimeout = 30 * time.Second

type Client struct {
	baseURL   string
	apiKey    string
	http      *http.Client
	retryWait time.Duration
}

type Option func(*Client)

func WithHTTPClient(client *http.Client) Option {
	return func(c *Client) {
		if client != nil {
			c.http = client
		}
	}
}

func WithRetryWait(wait time.Duration) Option {
	return func(c *Client) {
		c.retryWait = wait
	}
}

func NewClient(baseURL string, apiKey string, opts ...Option) *Client {
	client := &Client{
		baseURL:   strings.TrimRight(baseURL, "/"),
		apiKey:    apiKey,
		http:      &http.Client{Timeout: defaultTimeout},
		retryWait: 200 * time.Millisecond,
	}
	for _, opt := range opts {
		opt(client)
	}
	return client
}

type StatusError struct {
	StatusCode int
	URL        string
	Body       string
}

func (e *StatusError) Error() string {
	return fmt.Sprintf("onyx returned %d for %s: %s", e.StatusCode, e.URL, e.Body)
}

type Persona struct {
	ID           int    `json:"id"`
	Name         string `json:"name"`
	Description  string `json:"description"`
	SystemPrompt string `json:"system_prompt,omitempty"`
}

type ChatSession struct {
	ID          string `json:"id"`
	PersonaID   int    `json:"persona_id"`
	Description string `json:"description"`
}

type SearchHit struct {
	DocumentID         string         `json:"document_id"`
	SemanticIdentifier string         `json:"semantic_identifier"`
	Link               string         `json:"link"`
	Blurb              string         `json:"blurb"`
	Score              float64        `json:"score"`
	UpdatedAt          string         `json:"updated_at"`
	Metadata           map[string]any `json:"metadata"`
}

type ChatResult struct {
	Text      string           `json:"text"`
	Citations map[int]string   `json:"citations"`
	Documents []map[string]any `json:"documents"`
	MessageID *int             `json:"message_id"`
}

type IngestResult struct {
	DocumentID     string `json:"document_id"`
	AlreadyExisted bool   `json:"already_existed"`
}

type DocSet struct {
	ID          int    `json:"id"`
	Name        string `json:"name"`
	Description string `json:"description"`
}

func (c *Client) Ping(ctx context.Context) string {
	req, err := c.newRequest(ctx, http.MethodGet, "/api/health", nil)
	if err != nil {
		return "unreachable"
	}
	client := *c.http
	client.Timeout = 5 * time.Second
	resp, err := client.Do(req)
	if err != nil {
		return "unreachable"
	}
	defer resp.Body.Close()
	if resp.StatusCode == http.StatusOK {
		return "reachable"
	}
	return "unreachable"
}

func (c *Client) ListPersonas(ctx context.Context) ([]Persona, error) {
	var raw json.RawMessage
	if err := c.doJSON(ctx, http.MethodGet, "/api/persona", nil, &raw); err != nil {
		return nil, err
	}

	var list []Persona
	if err := json.Unmarshal(raw, &list); err == nil {
		return list, nil
	}

	var envelope struct {
		Personas []Persona `json:"personas"`
	}
	if err := json.Unmarshal(raw, &envelope); err != nil {
		return nil, err
	}
	return envelope.Personas, nil
}

type CreatePersonaRequest struct {
	Name                     string
	Description              string
	SystemPrompt             string
	DocumentSetIDs           []int
	ToolIDs                  []int
	LLMModelProviderOverride *string
	LLMModelVersionOverride  *string
	NumChunks                int
	LLMRelevanceFilter       bool
	IncludeCitations         bool
}

func (c *Client) CreatePersona(ctx context.Context, req CreatePersonaRequest) (Persona, error) {
	numChunks := req.NumChunks
	if numChunks == 0 {
		numChunks = 10
	}
	body := map[string]any{
		"name":                        req.Name,
		"description":                 req.Description,
		"system_prompt":               req.SystemPrompt,
		"task_prompt":                 "",
		"document_set_ids":            req.DocumentSetIDs,
		"tool_ids":                    req.ToolIDs,
		"is_public":                   false,
		"llm_model_provider_override": req.LLMModelProviderOverride,
		"llm_model_version_override":  req.LLMModelVersionOverride,
		"num_chunks":                  numChunks,
		"llm_relevance_filter":        req.LLMRelevanceFilter,
		"include_citations":           req.IncludeCitations,
		"datetime_aware":              true,
		"starter_messages":            []string{},
	}

	var persona Persona
	err := c.doJSON(ctx, http.MethodPost, "/api/persona", body, &persona)
	return persona, err
}

func (c *Client) UpdatePersona(ctx context.Context, personaID int, fields map[string]any) (Persona, error) {
	var persona Persona
	err := c.doJSON(ctx, http.MethodPatch, "/api/persona/"+strconv.Itoa(personaID), fields, &persona)
	return persona, err
}

func (c *Client) CreateChatSession(ctx context.Context, personaID int, description string) (ChatSession, error) {
	var raw map[string]any
	err := c.doJSON(
		ctx,
		http.MethodPost,
		"/api/chat/create-chat-session",
		map[string]any{"persona_id": personaID, "description": description},
		&raw,
	)
	if err != nil {
		return ChatSession{}, err
	}

	sessionID := rawString(raw, "chat_session_id")
	if sessionID == "" {
		sessionID = rawString(raw, "id")
	}
	return ChatSession{ID: sessionID, PersonaID: personaID, Description: description}, nil
}

func (c *Client) AdminSearch(ctx context.Context, query string, filters map[string]any, limit int) ([]SearchHit, error) {
	if filters == nil {
		filters = map[string]any{}
	}
	var envelope struct {
		Documents []SearchHit `json:"documents"`
	}
	err := c.doJSON(
		ctx,
		http.MethodPost,
		"/api/admin/search",
		map[string]any{"query": query, "filters": filters, "limit": limit},
		&envelope,
	)
	return envelope.Documents, err
}

type IngestDocumentRequest struct {
	DocID              string
	Text               string
	SemanticIdentifier string
	Metadata           map[string]any
	SourceURL          string
	DocUpdatedAt       string
	Title              string
	CCPairID           *int
}

func (c *Client) IngestDocument(ctx context.Context, req IngestDocumentRequest) (IngestResult, error) {
	title := req.Title
	if title == "" {
		title = req.SemanticIdentifier
	}
	body := map[string]any{
		"document": map[string]any{
			"id":                  req.DocID,
			"sections":            []map[string]any{{"text": req.Text, "link": req.SourceURL}},
			"source":              "ingestion_api",
			"semantic_identifier": req.SemanticIdentifier,
			"metadata":            req.Metadata,
			"doc_updated_at":      req.DocUpdatedAt,
			"title":               title,
		},
		"cc_pair_id": req.CCPairID,
	}

	var result IngestResult
	err := c.doJSON(ctx, http.MethodPost, "/api/onyx-api/ingestion", body, &result)
	return result, err
}

func (c *Client) ListDocumentSets(ctx context.Context) ([]DocSet, error) {
	var raw json.RawMessage
	if err := c.doJSON(ctx, http.MethodGet, "/api/document-set", nil, &raw); err != nil {
		return nil, err
	}

	var list []DocSet
	if err := json.Unmarshal(raw, &list); err == nil {
		return list, nil
	}

	var envelope struct {
		DocumentSets []DocSet `json:"document_sets"`
	}
	if err := json.Unmarshal(raw, &envelope); err != nil {
		return nil, err
	}
	return envelope.DocumentSets, nil
}

func (c *Client) CreateDocumentSet(ctx context.Context, name string, description string, ccPairIDs []int) (DocSet, error) {
	if ccPairIDs == nil {
		ccPairIDs = []int{}
	}
	var docSet DocSet
	err := c.doJSON(
		ctx,
		http.MethodPost,
		"/api/admin/document-set",
		map[string]any{"name": name, "description": description, "cc_pair_ids": ccPairIDs},
		&docSet,
	)
	return docSet, err
}

func (c *Client) SendMessageSync(
	ctx context.Context,
	chatSessionID string,
	parentMessageID *int,
	message string,
	searchDocIDs []int,
) (ChatResult, error) {
	body := map[string]any{
		"chat_session_id":           chatSessionID,
		"parent_message_id":         parentMessageID,
		"message":                   message,
		"prompt_id":                 nil,
		"search_doc_ids":            searchDocIDs,
		"file_descriptors":          []string{},
		"retrieval_options":         map[string]any{"run_search": "always", "real_time": true},
		"query_override":            nil,
		"use_existing_user_message": false,
	}
	raw, err := c.doRaw(ctx, http.MethodPost, "/api/chat/send-chat-message", body)
	if err != nil {
		return ChatResult{}, err
	}
	return ParseChatStream(raw), nil
}

func ParseChatStream(body []byte) ChatResult {
	result := ChatResult{
		Citations: map[int]string{},
		Documents: []map[string]any{},
	}
	for _, rawLine := range bytes.Split(body, []byte("\n")) {
		line := bytes.TrimSpace(rawLine)
		if len(line) == 0 {
			continue
		}
		var obj map[string]any
		if err := json.Unmarshal(line, &obj); err != nil {
			continue
		}
		if piece, ok := obj["answer_piece"].(string); ok {
			result.Text += piece
		}
		if citations, ok := obj["citations"].(map[string]any); ok {
			for key, value := range citations {
				index, err := strconv.Atoi(key)
				if err != nil {
					continue
				}
				result.Citations[index] = fmt.Sprint(value)
			}
		}
		if documents, ok := obj["documents"].([]any); ok {
			for _, doc := range documents {
				if row, ok := doc.(map[string]any); ok {
					result.Documents = append(result.Documents, row)
				}
			}
		}
		if id, ok := numberAsInt(obj["message_id"]); ok {
			result.MessageID = &id
		}
	}
	return result
}

func (c *Client) doJSON(ctx context.Context, method string, path string, body any, out any) error {
	raw, err := c.doRaw(ctx, method, path, body)
	if err != nil {
		return err
	}
	if out == nil {
		return nil
	}
	if rawMessage, ok := out.(*json.RawMessage); ok {
		*rawMessage = append((*rawMessage)[:0], raw...)
		return nil
	}
	return json.Unmarshal(raw, out)
}

func (c *Client) doRaw(ctx context.Context, method string, path string, body any) ([]byte, error) {
	var lastErr error
	for attempt := 0; attempt < 3; attempt++ {
		req, err := c.newRequest(ctx, method, path, body)
		if err != nil {
			return nil, err
		}

		resp, err := c.http.Do(req)
		if err != nil {
			lastErr = err
			if !isRetryableError(err) {
				return nil, err
			}
			c.waitBeforeRetry(attempt)
			continue
		}

		raw, readErr := io.ReadAll(resp.Body)
		resp.Body.Close()
		if readErr != nil {
			return nil, readErr
		}

		if resp.StatusCode >= 500 {
			lastErr = &StatusError{StatusCode: resp.StatusCode, URL: req.URL.String(), Body: truncate(string(raw), 200)}
			c.waitBeforeRetry(attempt)
			continue
		}
		if resp.StatusCode == http.StatusUnauthorized || resp.StatusCode == http.StatusForbidden || resp.StatusCode == http.StatusNotFound || resp.StatusCode >= 400 {
			return nil, &StatusError{StatusCode: resp.StatusCode, URL: req.URL.String(), Body: truncate(string(raw), 200)}
		}
		return raw, nil
	}
	if lastErr != nil {
		return nil, lastErr
	}
	return nil, errors.New("onyx request failed")
}

func (c *Client) newRequest(ctx context.Context, method string, path string, body any) (*http.Request, error) {
	var reader io.Reader
	if body != nil {
		raw, err := json.Marshal(body)
		if err != nil {
			return nil, err
		}
		reader = bytes.NewReader(raw)
	}
	req, err := http.NewRequestWithContext(ctx, method, c.fullURL(path), reader)
	if err != nil {
		return nil, err
	}
	req.Header.Set("Accept", "application/json")
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	if c.apiKey != "" {
		req.Header.Set("Authorization", "Bearer "+c.apiKey)
	}
	return req, nil
}

func (c *Client) fullURL(path string) string {
	if _, err := url.ParseRequestURI(path); err == nil && strings.HasPrefix(path, "http") {
		return path
	}
	return c.baseURL + path
}

func (c *Client) waitBeforeRetry(attempt int) {
	if c.retryWait <= 0 || attempt >= 2 {
		return
	}
	time.Sleep(c.retryWait * time.Duration(1<<attempt))
}

func isRetryableError(err error) bool {
	var netErr interface{ Timeout() bool }
	if errors.As(err, &netErr) && netErr.Timeout() {
		return true
	}
	return true
}

func rawString(raw map[string]any, key string) string {
	value, ok := raw[key]
	if !ok || value == nil {
		return ""
	}
	return fmt.Sprint(value)
}

func numberAsInt(value any) (int, bool) {
	switch typed := value.(type) {
	case int:
		return typed, true
	case int64:
		return int(typed), true
	case float64:
		return int(typed), true
	default:
		return 0, false
	}
}

func truncate(value string, limit int) string {
	if len(value) <= limit {
		return value
	}
	return value[:limit]
}
