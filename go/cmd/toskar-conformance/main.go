// Command toskar-conformance runs the shared conformance cases
// (conformance/README.md) with the Go SDK.
package main

import (
	"context"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"time"

	toskar "github.com/yeixio/toskar-sdks/go"
	"github.com/yeixio/toskar-sdks/go/api"
)

func main() {
	out, err := run(os.Args[1:])
	if err != nil {
		out = map[string]any{"error": map[string]string{"code": codeOf(err), "message": err.Error()}}
	}
	_ = json.NewEncoder(os.Stdout).Encode(out)
	if err != nil {
		os.Exit(1)
	}
}

func run(args []string) (any, error) {
	ctx, cancel := context.WithTimeout(context.Background(), time.Minute)
	defer cancel()
	switch {
	case len(args) == 3 && args[0] == "pair":
		var short string
		d, err := toskar.Pair(ctx, args[1], args[2], "Go conformance", func(s string) bool { short = s; return true })
		if err != nil {
			return nil, err
		}
		return map[string]any{"device": d, "short_pin": short}, nil
	case len(args) == 2 && args[0] == "call":
		raw, err := os.ReadFile(args[1])
		if err != nil {
			return nil, err
		}
		var d toskar.Device
		if err := json.Unmarshal(raw, &d); err != nil {
			return nil, err
		}
		c, err := toskar.New(toskar.WithDevice(d), toskar.WithRetries(0))
		if err != nil {
			return nil, err
		}
		settings, err := toskar.Data(c.GetSettingsWithResponse(ctx))
		if err != nil {
			return nil, err
		}
		return map[string]any{"path": c.Path(), "node_name": settings["node_name"]}, nil
	}
	// The rest connect as TOSKAR_URL and TOSKAR_API_KEY say.
	c, err := toskar.New(toskar.WithRetries(0))
	if err != nil {
		return nil, err
	}
	switch {
	case len(args) == 3 && args[0] == "chat":
		a, err := c.Chat(ctx, api.ChatJSONRequestBody{ModelId: &args[1], Message: args[2]})
		if err != nil {
			return nil, err
		}
		return map[string]any{"content": a.Content}, nil
	case len(args) == 3 && args[0] == "stream":
		var content strings.Builder
		tokens, done := 0, false
		for e, err := range c.ChatStream(ctx, api.ChatJSONRequestBody{ModelId: &args[1], Message: args[2]}) {
			if err != nil {
				return nil, err
			}
			switch e.Type {
			case "token":
				tokens++
				content.WriteString(e.Content)
			case "done":
				done = true
			}
		}
		return map[string]any{"content": content.String(), "tokens": tokens, "done": done}, nil
	case len(args) == 4 && args[0] == "events":
		return events(ctx, c, args[1], args[2], args[3])
	case len(args) == 2 && args[0] == "upload":
		raw, err := os.ReadFile(args[1])
		if err != nil {
			return nil, err
		}
		content := base64.StdEncoding.EncodeToString(raw)
		a, err := toskar.Data(c.UploadArtifactWithResponse(ctx, api.UploadArtifactJSONRequestBody{Name: filepath.Base(args[1]), ContentBase64: &content}))
		if err != nil {
			return nil, err
		}
		return map[string]any{"id": a.Id, "name": a.Name, "size_bytes": a.SizeBytes}, nil
	case len(args) == 2 && args[0] == "download":
		r, err := c.GetArtifactContentWithResponse(ctx, args[1], nil)
		if err := toskar.Check(r, err); err != nil {
			return nil, err
		}
		sum := sha256.Sum256(r.Body)
		return map[string]any{"sha256": hex.EncodeToString(sum[:]), "size_bytes": len(r.Body)}, nil
	}
	return nil, errors.New("usage: toskar-conformance pair <address> <code> | call <device.json> | chat|stream <model> <message> | events <model> <message> <until> | upload <file> | download <id>")
}

// events listens to the events stream, asks once, and lists the events'
// types until one of type until.
func events(ctx context.Context, c *toskar.Client, model, message, until string) (any, error) {
	ctx, cancel := context.WithTimeout(ctx, 30*time.Second)
	defer cancel()
	var types []string
	done := make(chan error, 1)
	go func() {
		for e, err := range c.Events(ctx) {
			if err != nil {
				done <- err
				return
			}
			types = append(types, e.Type)
			if e.Type == until {
				done <- nil
				return
			}
		}
		done <- ctx.Err()
	}()
	// Time to subscribe before asking.
	time.Sleep(time.Second)
	if _, err := c.Chat(ctx, api.ChatJSONRequestBody{ModelId: &model, Message: message}); err != nil {
		return nil, err
	}
	if err := <-done; err != nil {
		return nil, err
	}
	return map[string]any{"types": types}, nil
}

func codeOf(err error) string {
	var e *toskar.APIError
	switch {
	case errors.As(err, &e):
		return e.Code
	case errors.Is(err, toskar.ErrPinMismatch):
		return "PIN_MISMATCH"
	case errors.Is(err, toskar.ErrNotConfirmed):
		return "NOT_CONFIRMED"
	case errors.Is(err, toskar.ErrNoRecord):
		return "NO_RECORD"
	case errors.Is(err, toskar.ErrUnreachable):
		return "UNREACHABLE"
	}
	return "ERROR"
}
