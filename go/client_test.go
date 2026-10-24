package toskar_test

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync/atomic"
	"testing"

	toskar "github.com/yeixio/toskar-sdks/go"
	"github.com/yeixio/toskar-sdks/go/api"
)

func core(t *testing.T, handler http.HandlerFunc) *toskar.Client {
	t.Helper()
	srv := httptest.NewServer(handler)
	t.Cleanup(srv.Close)
	c, err := toskar.New(toskar.WithURL(srv.URL), toskar.WithKey("tk_test"))
	if err != nil {
		t.Fatal(err)
	}
	return c
}

func sse(w http.ResponseWriter, chunks ...string) {
	w.Header().Set("Content-Type", "text/event-stream")
	for _, c := range chunks {
		_, _ = io.WriteString(w, c)
		w.(http.Flusher).Flush()
	}
}

func TestSaysItsContractAndSendsTheKey(t *testing.T) {
	c := core(t, func(w http.ResponseWriter, r *http.Request) {
		if r.Header.Get("Toskar-Client-Contract") != toskar.ContractVersion || r.Header.Get("Authorization") != "Bearer tk_test" {
			t.Errorf("headers: %v", r.Header)
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = io.WriteString(w, `{"version":"1.11.0","commit":"abc","build_date":"2026-10-23","product":"Toskar Core","license":"AGPL-3.0","source":"x","contract":{"version":"1.56","major":1}}`)
	})
	v, err := c.Version(context.Background())
	if err != nil || v.Version != "1.11.0" {
		t.Fatalf("version: %+v %v", v, err)
	}
}

func TestChatsWaitingForTheWholeAnswer(t *testing.T) {
	c := core(t, func(w http.ResponseWriter, r *http.Request) {
		var body map[string]any
		_ = json.NewDecoder(r.Body).Decode(&body)
		if body["message"] != "Hi" || body["stream"] != false {
			t.Errorf("body: %v", body)
		}
		_, _ = io.WriteString(w, `{"content":"Hello!"}`)
	})
	answer, err := c.Chat(context.Background(), api.ChatJSONRequestBody{Message: "Hi"})
	if err != nil || answer.Content != "Hello!" {
		t.Fatalf("chat: %+v %v", answer, err)
	}
}

func TestStreamsAnAnswerAsItIsWritten(t *testing.T) {
	c := core(t, func(w http.ResponseWriter, r *http.Request) {
		sse(w, "event: token\ndata: {\"content\":\"Hel\"}\n\n: ping\n\nevent: tok", "en\ndata: {\"content\":\"lo\"}\n\n", "event: done\ndata: {}\n\n")
	})
	var got []string
	for e, err := range c.ChatStream(context.Background(), api.ChatJSONRequestBody{Message: "Hi"}) {
		if err != nil {
			t.Fatal(err)
		}
		got = append(got, e.Type+":"+e.Content)
	}
	if strings.Join(got, ",") != "token:Hel,token:lo,done:" {
		t.Fatalf("events: %v", got)
	}
}

func TestAStreamedFailureHasItsCode(t *testing.T) {
	c := core(t, func(w http.ResponseWriter, r *http.Request) {
		sse(w, "event: error_code\ndata: {\"code\":\"MODEL_NOT_INSTALLED\",\"message\":\"model x is not installed\",\"details\":{\"model_id\":\"x\"}}\n\n", "event: error\ndata: model x is not installed\n\n")
	})
	var got error
	for _, err := range c.ChatStream(context.Background(), api.ChatJSONRequestBody{Message: "Hi"}) {
		got = err
	}
	var e *toskar.APIError
	if !errors.As(got, &e) || e.Code != toskar.ErrorCodeModelNotInstalled || e.Details["model_id"] != "x" {
		t.Fatalf("error: %v", got)
	}
}

func TestACutOffStreamSaysSo(t *testing.T) {
	c := core(t, func(w http.ResponseWriter, r *http.Request) { sse(w, "event: token\ndata: {\"content\":\"Hi\"}\n\n") })
	var got error
	for _, err := range c.ChatStream(context.Background(), api.ChatJSONRequestBody{Message: "Hi"}) {
		got = err
	}
	var e *toskar.APIError
	if !errors.As(got, &e) || e.Code != "CONNECTION_LOST" {
		t.Fatalf("error: %v", got)
	}
}

func TestAnErrorAnswerIsAnAPIError(t *testing.T) {
	c := core(t, func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusUnauthorized)
		_, _ = io.WriteString(w, `{"error":{"code":"API_KEY_REQUIRED","message":"an API key is required"}}`)
	})
	_, err := c.Chat(context.Background(), api.ChatJSONRequestBody{Message: "Hi"})
	var e *toskar.APIError
	if !errors.As(err, &e) || e.Status != 401 || e.Code != toskar.ErrorCodeApiKeyRequired {
		t.Fatalf("error: %v", err)
	}
	if _, err := toskar.Data(c.ListModelsWithResponse(context.Background())); !errors.As(err, &e) || e.Code != "API_KEY_REQUIRED" {
		t.Fatalf("data error: %v", err)
	}
}

func TestRetriesASafeRequestButNeverAChat(t *testing.T) {
	var models, chats atomic.Int32
	c := core(t, func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/api/v1/chat" {
			chats.Add(1)
			w.WriteHeader(http.StatusServiceUnavailable)
			return
		}
		if models.Add(1) < 3 {
			w.WriteHeader(http.StatusServiceUnavailable)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = io.WriteString(w, `[]`)
	})
	list, err := toskar.Data(c.ListModelsWithResponse(context.Background()))
	if err != nil || len(list) != 0 || models.Load() != 3 {
		t.Fatalf("models: %v %v after %d tries", list, err, models.Load())
	}
	if _, err := c.Chat(context.Background(), api.ChatJSONRequestBody{Message: "Hi"}); err == nil || chats.Load() != 1 {
		t.Fatalf("chat: %v after %d tries", err, chats.Load())
	}
}

func TestEveryRouteIsTyped(t *testing.T) {
	c := core(t, func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusCreated)
		_, _ = io.WriteString(w, `{"id":"c1","title":"Trip","memory_off":false,"compact_off":false,"created_at":"2026-10-23T00:00:00Z","updated_at":"2026-10-23T00:00:00Z","a_newer_field":1}`)
	})
	title := "Trip"
	r, err := c.CreateConversationWithResponse(context.Background(), api.CreateConversationJSONRequestBody{Title: &title})
	if err != nil || r.JSON201 == nil || r.JSON201.Id != "c1" {
		t.Fatalf("conversation: %+v %v", r, err)
	}
}

func TestReadsTheEventsStream(t *testing.T) {
	c := core(t, func(w http.ResponseWriter, r *http.Request) {
		sse(w, "event: model.unloaded\ndata: {\"id\":\"e1\",\"type\":\"model.unloaded\",\"timestamp\":\"2026-10-23T00:00:00Z\",\"contract\":\"1.56\"}\n\n")
	})
	var types []string
	for e, err := range c.Events(context.Background()) {
		if err != nil {
			t.Fatal(err)
		}
		types = append(types, e.Type)
	}
	if strings.Join(types, ",") != "model.unloaded" {
		t.Fatalf("events: %v", types)
	}
}

func TestReadEvents(t *testing.T) {
	var got []string
	for e, err := range toskar.ReadEvents(strings.NewReader("event: a\ndata: 1\ndata: 2\n\n: ping\n\ndata: plain\n")) {
		if err != nil {
			t.Fatal(err)
		}
		got = append(got, e.Event+"="+e.Data)
	}
	if strings.Join(got, "|") != "a=1\n2|message=plain" {
		t.Fatalf("events: %q", got)
	}
}
