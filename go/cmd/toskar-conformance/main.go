// Command toskar-conformance runs the shared conformance cases
// (conformance/README.md) with the Go SDK.
package main

import (
	"context"
	"encoding/json"
	"errors"
	"os"
	"time"

	toskar "github.com/yeixio/toskar-sdks/go"
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
	return nil, errors.New("usage: toskar-conformance pair <address> <code> | call <device.json>")
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
