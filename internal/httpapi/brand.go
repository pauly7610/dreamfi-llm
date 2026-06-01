package httpapi

import (
	_ "embed"
	"net/http"
)

//go:embed dreamfi-logo.svg
var dreamfiLogoSVG []byte

func (s *Server) dreamfiLogo(w http.ResponseWriter, _ *http.Request) {
	w.Header().Set("Content-Type", "image/svg+xml; charset=utf-8")
	w.Header().Set("Cache-Control", "public, max-age=31536000, immutable")
	w.WriteHeader(http.StatusOK)
	_, _ = w.Write(dreamfiLogoSVG)
}
