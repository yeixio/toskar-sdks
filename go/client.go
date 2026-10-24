package toskar

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"iter"
	"math/rand/v2"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/yeixio/toskar-sdks/go/api"
)

// DefaultURL is this computer's Toskar Core, which needs no key.
const DefaultURL = "http://127.0.0.1:7331"

// Client is a connection to Toskar Core.
//
// Its embedded api.ClientWithResponses reaches every route, typed from Core's
// API spec, and Data unwraps an answer:
//
//	models, err := toskar.Data(c.ListModelsWithResponse(ctx))
//
// and its own methods cover what's easier by hand: Chat, ChatStream, and
// Events.
type Client struct {
	*api.ClientWithResponses
	BaseURL string
	http    *http.Client
	headers http.Header
}

type options struct {
	baseURL string
	apiKey  string
	retries int
	timeout time.Duration
	http    *http.Client
	headers http.Header
}

// An Option changes how New connects.
type Option func(*options)

// WithURL is where Toskar Core answers. Default: TOSKAR_URL, or
// DefaultURL, this computer.
func WithURL(url string) Option { return func(o *options) { o.baseURL = url } }

// WithKey is the API key for any address other than this computer's
// loopback. Default: TOSKAR_API_KEY.
func WithKey(key string) Option { return func(o *options) { o.apiKey = key } }

// WithRetries is how many times a safe request (GET, HEAD, OPTIONS) that
// fails to connect or answers 502, 503, or 504 is retried. Default 2.
func WithRetries(n int) Option { return func(o *options) { o.retries = n } }

// WithTimeout is how long to wait for an answer to start; a streamed answer
// then runs for as long as it takes. Default 60 seconds; 0 waits as long as
// it takes. It applies to the default HTTP client only.
func WithTimeout(d time.Duration) Option { return func(o *options) { o.timeout = d } }

// WithHTTP sends requests with c in place of the default client.
func WithHTTP(c *http.Client) Option { return func(o *options) { o.http = c } }

// WithHeader adds a header to every request.
func WithHeader(name, value string) Option {
	return func(o *options) { o.headers.Add(name, value) }
}

// New connects to Toskar Core.
func New(opts ...Option) (*Client, error) {
	o := options{retries: 2, timeout: 60 * time.Second, headers: http.Header{}}
	for _, opt := range opts {
		opt(&o)
	}
	if o.baseURL == "" {
		o.baseURL = os.Getenv("TOSKAR_URL")
	}
	if o.baseURL == "" {
		o.baseURL = DefaultURL
	}
	o.baseURL = strings.TrimRight(o.baseURL, "/")
	if o.apiKey == "" {
		o.apiKey = os.Getenv("TOSKAR_API_KEY")
	}
	// Core answers 426 CONTRACT_MISMATCH to a client of another major version.
	o.headers.Set("Toskar-Client-Contract", ContractVersion)
	if o.apiKey != "" {
		o.headers.Set("Authorization", "Bearer "+o.apiKey)
	}
	hc := o.http
	if hc == nil {
		transport := http.DefaultTransport.(*http.Transport).Clone()
		transport.ResponseHeaderTimeout = o.timeout
		hc = &http.Client{Transport: transport}
	}
	hc = &http.Client{
		Transport:     &retrying{next: transportOf(hc), retries: o.retries},
		CheckRedirect: hc.CheckRedirect,
		Jar:           hc.Jar,
		Timeout:       hc.Timeout,
	}
	c := &Client{BaseURL: o.baseURL, http: hc, headers: o.headers}
	generated, err := api.NewClientWithResponses(o.baseURL, api.WithHTTPClient(hc), api.WithRequestEditorFn(func(_ context.Context, r *http.Request) error {
		for name, values := range c.headers {
			r.Header[name] = values
		}
		return nil
	}))
	if err != nil {
		return nil, err
	}
	c.ClientWithResponses = generated
	return c, nil
}

func transportOf(c *http.Client) http.RoundTripper {
	if c.Transport != nil {
		return c.Transport
	}
	return http.DefaultTransport
}

// retrying retries safe requests that fail to connect or answer 502, 503,
// or 504, with backoff. A chat is never retried: it could answer twice.
type retrying struct {
	next    http.RoundTripper
	retries int
}

func (t *retrying) RoundTrip(r *http.Request) (*http.Response, error) {
	attempts := 1
	if r.Method == http.MethodGet || r.Method == http.MethodHead || r.Method == http.MethodOptions {
		attempts += t.retries
	}
	for attempt := 1; ; attempt++ {
		resp, err := t.next.RoundTrip(r)
		if attempt >= attempts || r.Context().Err() != nil {
			return resp, err
		}
		if err == nil {
			switch resp.StatusCode {
			case http.StatusBadGateway, http.StatusServiceUnavailable, http.StatusGatewayTimeout:
				_, _ = io.Copy(io.Discard, resp.Body)
				resp.Body.Close()
			default:
				return resp, nil
			}
		}
		wait := time.Duration(200<<(attempt-1))*time.Millisecond + time.Duration(rand.IntN(100))*time.Millisecond
		select {
		case <-time.After(wait):
		case <-r.Context().Done():
			return nil, r.Context().Err()
		}
	}
}

// Chat asks once and waits for the whole answer. Stream is set for you.
func (c *Client) Chat(ctx context.Context, req api.ChatJSONRequestBody) (*api.ChatAnswer, error) {
	req.Stream = ptr(false)
	resp, err := c.post(ctx, "/api/v1/chat", req, "application/json")
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	var answer api.ChatAnswer
	if err := json.NewDecoder(resp.Body).Decode(&answer); err != nil {
		return nil, err
	}
	return &answer, nil
}

// ChatStreamEvent is one event of a streamed chat: a token with the next
// piece of the answer (Type "token", Content), or done once it's finished
// and saved (Type "done", Metrics when the runtime reported them).
type ChatStreamEvent struct {
	Type    string
	Content string
	Metrics *api.GenerationMetrics
}

// ChatStream asks and yields the answer as it's written: tokens, then done.
// A failure is yielded as an *APIError with its code, such as
// ErrorCodeNoModelInstalled, and ends the stream.
//
//	for e, err := range c.ChatStream(ctx, toskar.ChatJSONRequestBody{Message: "Hi"}) {
//		if err != nil { return err }
//		if e.Type == "token" { fmt.Print(e.Content) }
//	}
func (c *Client) ChatStream(ctx context.Context, req api.ChatJSONRequestBody) iter.Seq2[ChatStreamEvent, error] {
	return func(yield func(ChatStreamEvent, error) bool) {
		req.Stream = ptr(true)
		resp, err := c.post(ctx, "/api/v1/chat", req, "text/event-stream")
		if err != nil {
			yield(ChatStreamEvent{}, err)
			return
		}
		defer resp.Body.Close()
		for e, err := range ReadEvents(resp.Body) {
			if err != nil {
				yield(ChatStreamEvent{}, err)
				return
			}
			switch e.Event {
			case "token":
				var t api.ChatToken
				if err := json.Unmarshal([]byte(e.Data), &t); err != nil {
					yield(ChatStreamEvent{}, err)
					return
				}
				if !yield(ChatStreamEvent{Type: "token", Content: t.Content}, nil) {
					return
				}
			case "done":
				var d api.ChatDone
				_ = json.Unmarshal([]byte(e.Data), &d)
				yield(ChatStreamEvent{Type: "done", Metrics: d.Metrics}, nil)
				return
			case "error_code":
				var b api.ErrorBody
				_ = json.Unmarshal([]byte(e.Data), &b)
				var details map[string]any
				if b.Details != nil {
					details = *b.Details
				}
				yield(ChatStreamEvent{}, &APIError{Status: resp.StatusCode, Code: b.Code, Message: b.Message, Details: details})
				return
			case "error":
				yield(ChatStreamEvent{}, &APIError{Status: resp.StatusCode, Code: ErrorCodeChatFailed, Message: e.Data})
				return
			}
		}
		// Every stream ends with done or an error, so one that just stops was cut off.
		yield(ChatStreamEvent{}, &APIError{Status: resp.StatusCode, Code: "CONNECTION_LOST", Message: "The answer stopped before it finished"})
	}
}

// Events yields what happens on Toskar as it happens, such as models
// loading and automations running, until ctx is done or you stop.
func (c *Client) Events(ctx context.Context) iter.Seq2[api.Event, error] {
	return func(yield func(api.Event, error) bool) {
		r, err := http.NewRequestWithContext(ctx, http.MethodGet, c.BaseURL+"/api/v1/events", nil)
		if err != nil {
			yield(api.Event{}, err)
			return
		}
		c.setHeaders(r, "text/event-stream")
		resp, err := c.http.Do(r)
		if err != nil {
			yield(api.Event{}, err)
			return
		}
		defer resp.Body.Close()
		if resp.StatusCode >= 300 {
			body, _ := io.ReadAll(resp.Body)
			yield(api.Event{}, errorFrom(resp.StatusCode, body))
			return
		}
		for e, err := range ReadEvents(resp.Body) {
			if err != nil {
				if ctx.Err() == nil {
					yield(api.Event{}, err)
				}
				return
			}
			var ev api.Event
			if err := json.Unmarshal([]byte(e.Data), &ev); err != nil {
				yield(api.Event{}, err)
				return
			}
			if !yield(ev, nil) {
				return
			}
		}
	}
}

// Version is Core's version and its client contract.
func (c *Client) Version(ctx context.Context) (api.VersionResponse, error) {
	return Data(c.GetVersionWithResponse(ctx))
}

func (c *Client) setHeaders(r *http.Request, accept string) {
	for name, values := range c.headers {
		r.Header[name] = values
	}
	r.Header.Set("Accept", accept)
}

func (c *Client) post(ctx context.Context, path string, body any, accept string) (*http.Response, error) {
	raw, err := json.Marshal(body)
	if err != nil {
		return nil, err
	}
	r, err := http.NewRequestWithContext(ctx, http.MethodPost, c.BaseURL+path, bytes.NewReader(raw))
	if err != nil {
		return nil, err
	}
	c.setHeaders(r, accept)
	r.Header.Set("Content-Type", "application/json")
	resp, err := c.http.Do(r)
	if err != nil {
		return nil, err
	}
	if resp.StatusCode >= 300 {
		defer resp.Body.Close()
		b, _ := io.ReadAll(resp.Body)
		return nil, errorFrom(resp.StatusCode, b)
	}
	return resp, nil
}

func ptr[T any](v T) *T { return &v }
