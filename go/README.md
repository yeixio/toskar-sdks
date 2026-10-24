# Toskar for Go

The official Go SDK for [Toskar](https://toskar.ai). It needs Go 1.24 or later.

```bash
go get github.com/yeixio/toskar-sdks/go
```

Every class, function, and type: [the reference](../reference/go/README.md).

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

## Pairing, as the Toskar apps do

An app can pair as a device, with the code **Connect a device** shows on the computer, instead of using an API key. It then reaches its computer at home and, when the computer has access from anywhere, directly or through its relay, always pinned to the computer's own certificate ([how it works](https://github.com/yeixio/toskar-core/blob/main/docs/connecting.md)).

```go
// On the computer's network, with the code it shows:
device, err := toskar.Pair(ctx, "192.168.1.20:7331", "123456", "Kitchen tablet", func(short string) bool {
	// Show short, such as 9B80-D9D9, and ask whether the computer shows the same.
	return askThePerson(short)
})
// Save device, as a password is saved: its key and route are secrets.

c, err := toskar.New(toskar.WithDevice(*device))
models, err := toskar.Data(c.ListModelsWithResponse(ctx))
fmt.Println(c.Path()) // home, direct, or relay
```

Every connection checks the computer's certificate before anything is sent. A different certificate stops with `toskar.ErrPinMismatch`, and is never accepted on its own: pair again to trust a new one. Away from home, the client opens the computer's sealed address record from its relay, tries its direct ways in at once and the relay a second later, and keeps the first that answers. `c.Reconnect(ctx)` chooses again, as after the network changes. A device key reaches the routes a device needs. Scripts and servers that need the rest use a key from API Access.

## Find computers on the network

Computers running Toskar announce themselves on the home network (mDNS, `_localai._tcp`). `discover.Find` lists them, so a person can pick one instead of typing an address:

```go
import "github.com/yeixio/toskar-sdks/go/discover"

computers, err := discover.Find(ctx, 3*time.Second)
for _, c := range computers {
	fmt.Println(c.Name, c.Address)
}
```

Pair with `c.Address`. When `c.OnNetwork` is false, the computer answers only on itself: tell the person to turn on Connect a device there, rather than that it's unreachable. A computer can advertise addresses this device can't reach, such as a container network's; `Address` is the first one that answers, and `Addresses` has them all.
