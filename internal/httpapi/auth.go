package httpapi

import (
	"context"
	"crypto/subtle"
	"encoding/base64"
	"net/http"
	"strings"

	"github.com/pauly7610/dreamfi-llm/internal/config"
)

type authContextKey struct{}

type AuthContext struct {
	ActorID    string
	ActorType  string
	AuthMethod string
	Outcome    string
	Reason     string
}

var placeholderSecrets = map[string]struct{}{
	"":                        {},
	"change-me":               {},
	"change-me-before-deploy": {},
}

func AuthFromContext(ctx context.Context) AuthContext {
	auth, ok := ctx.Value(authContextKey{}).(AuthContext)
	if !ok {
		return AuthContext{ActorID: "anonymous", ActorType: "anonymous", AuthMethod: "none", Outcome: "unknown"}
	}
	return auth
}

func AuthMiddleware(settings config.Settings, next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/ready" || r.URL.Path == "/health" {
			next.ServeHTTP(w, stampAuth(r, AuthContext{
				ActorID:    "healthcheck",
				ActorType:  "system",
				AuthMethod: "exempt",
				Outcome:    "success",
			}))
			return
		}

		if !settings.AuthEnabled {
			next.ServeHTTP(w, stampAuth(r, AuthContext{
				ActorID:    "auth-disabled",
				ActorType:  "system",
				AuthMethod: "disabled",
				Outcome:    "success",
			}))
			return
		}

		expectedPassword := usableSecret(settings.AuthPassword)
		expectedToken := usableSecret(settings.APIToken)
		if expectedPassword == "" && expectedToken == "" {
			writeAuthFailure(w, r, http.StatusServiceUnavailable, "DreamFi auth is enabled but DREAMFI_AUTH_PASSWORD or DREAMFI_API_TOKEN is not configured", "auth_not_configured")
			return
		}

		authorization := r.Header.Get("Authorization")
		if authorization == "" {
			writeAuthFailure(w, r, http.StatusUnauthorized, "authentication required", "missing_credentials")
			return
		}

		if token, ok := bearerToken(authorization); ok && expectedToken != "" {
			if constantTimeEqual(token, expectedToken) {
				next.ServeHTTP(w, stampAuth(r, AuthContext{
					ActorID:    "api_token",
					ActorType:  "service_account",
					AuthMethod: "bearer",
					Outcome:    "success",
				}))
				return
			}
		}

		if username, password, ok := basicCredentials(authorization); ok && expectedPassword != "" {
			if constantTimeEqual(username, settings.AuthUsername) && constantTimeEqual(password, expectedPassword) {
				next.ServeHTTP(w, stampAuth(r, AuthContext{
					ActorID:    username,
					ActorType:  "user",
					AuthMethod: "basic",
					Outcome:    "success",
				}))
				return
			}
		}

		writeAuthFailure(w, r, http.StatusUnauthorized, "invalid credentials", "invalid_credentials")
	})
}

func stampAuth(r *http.Request, auth AuthContext) *http.Request {
	return r.WithContext(context.WithValue(r.Context(), authContextKey{}, auth))
}

func usableSecret(value string) string {
	trimmed := strings.TrimSpace(value)
	if _, ok := placeholderSecrets[trimmed]; ok {
		return ""
	}
	return trimmed
}

func bearerToken(value string) (string, bool) {
	scheme, token, ok := strings.Cut(value, " ")
	if !ok || !strings.EqualFold(scheme, "bearer") || strings.TrimSpace(token) == "" {
		return "", false
	}
	return strings.TrimSpace(token), true
}

func basicCredentials(value string) (string, string, bool) {
	scheme, encoded, ok := strings.Cut(value, " ")
	if !ok || !strings.EqualFold(scheme, "basic") || strings.TrimSpace(encoded) == "" {
		return "", "", false
	}
	raw, err := base64.StdEncoding.Strict().DecodeString(strings.TrimSpace(encoded))
	if err != nil {
		return "", "", false
	}
	username, password, ok := strings.Cut(string(raw), ":")
	if !ok {
		return "", "", false
	}
	return username, password, true
}

func constantTimeEqual(left string, right string) bool {
	return subtle.ConstantTimeCompare([]byte(left), []byte(right)) == 1
}

func writeAuthFailure(w http.ResponseWriter, r *http.Request, statusCode int, detail string, reason string) {
	w.Header().Set("WWW-Authenticate", `Basic realm="DreamFi", Bearer`)
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(statusCode)
	_, _ = w.Write([]byte(`{"detail":"` + detail + `"}`))
	_ = stampAuth(r, AuthContext{
		ActorID:    "anonymous",
		ActorType:  "anonymous",
		AuthMethod: "none",
		Outcome:    "failure",
		Reason:     reason,
	})
}
