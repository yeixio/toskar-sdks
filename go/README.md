# Toskar for Go

The official Go SDK for [Toskar](https://toskar.ai). It needs Go 1.24 or later.

```bash
go get github.com/yeixio/toskar-sdks/go
```

## Quick start

```go
package main

import (
	"context"
	"fmt"

	toskar "github.com/yeixio/toskar-sdks/go"
	"github.com/yeixio/toskar-sdks/go/api"
)

func main() {
	ctx := context.Background()
	// This computer's Toskar Core, at http://127.0.0.1:7331, needs no key.
	// Elsewhere: toskar.New(toskar.WithURL("http://studio.local:7331"), toskar.WithKey("tk_…")),
	// or set TOSKAR_URL and TOSKAR_API_KEY.
	c, err := toskar.New()
	if err != nil {
		panic(err)
	}

	// Stream an answer as it's written.
	for e, err := range c.ChatStream(ctx, api.ChatJSONRequestBody{Message: "Plan a three-day trip to Juneau"}) {
		if err != nil {
			panic(err)
		}
		if e.Type == "token" {
			fmt.Print(e.Content)
		}
	}

	// Or wait for the whole answer.
	answer, err := c.Chat(ctx, api.ChatJSONRequestBody{Message: "Summarize this in one line: …"})
	if err == nil {
		fmt.Println(answer.Content)
	}
}
```

## Every route, typed

Package `api` is generated from Toskar Core's API spec. `Client` embeds its client, so every operation is a method, and `toskar.Data` returns the answer, or the error:

```go
models, err := toskar.Data(c.ListModelsWithResponse(ctx)) // []api.Model
title := "Trip"
chat, err := toskar.Data(c.CreateConversationWithResponse(ctx, api.CreateConversationJSONRequestBody{Title: &title}))
messages, err := toskar.Data(c.ListConversationMessagesWithResponse(ctx, chat.Id))
```

Routes that answer 201 have `r.JSON201`. `toskar.Check` suits routes that answer nothing.

## Errors

Toskar answers errors with a stable code, as an `*toskar.APIError`:

```go
_, err := c.Chat(ctx, api.ChatJSONRequestBody{Message: "Hi"})
var e *toskar.APIError
if errors.As(err, &e) && e.Code == toskar.ErrorCodeNoModelInstalled {
	// Install one: c.InstallModelWithResponse(ctx, "qwen2.5-7b-q4", nil, api.InstallModelJSONRequestBody{})
}
```

A streamed answer that fails yields its error, with the code Toskar sent. One that stops before it finishes yields `CONNECTION_LOST`.

## Events

```go
for e, err := range c.Events(ctx) { // until ctx is done
	if err != nil {
		break
	}
	fmt.Println(e.Type) // such as model.download.progress or automation.completed
}
```

## Retries and timeouts

Safe requests (GET, HEAD, OPTIONS) that fail to connect, or that Toskar answers with 502, 503, or 504, are retried twice with backoff. A chat is never retried, since it could answer twice. Each request waits 60 seconds for its answer to start, and a streamed answer then runs for as long as it takes. Change these with `WithRetries` and `WithTimeout`, or bring your own client with `WithHTTP`.

## Not yet

- Pairing with a short code from Connect a device.
- Pinning a computer's certificate over its local-network HTTPS.
- Reaching it from anywhere through the relay, as the Toskar apps do.

They're coming next (toskar-core#666). For now, use an API key on the home network, or this computer's loopback.
