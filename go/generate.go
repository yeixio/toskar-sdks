// Package toskar is the official Go SDK for Toskar: local AI across your
// own computers.
//
//	c, err := toskar.New()
//	for e, err := range c.ChatStream(ctx, api.ChatJSONRequestBody{Message: "Hi"}) {
//		if err != nil { return err }
//		if e.Type == "token" { fmt.Print(e.Content) }
//	}
//
// Package api is every route, typed, generated from Toskar Core's API spec;
// Client embeds its client, and Data unwraps an answer.
package toskar

//go:generate go run github.com/oapi-codegen/oapi-codegen/v2/cmd/oapi-codegen@v2.8.1 -config oapi-codegen.yaml ../spec/openapi.sdk.json
//go:generate go run scripts/codes.go

// The reference docs, from these packages' doc comments. The repository is
// named so the source links are the same in CI's checkout.
//go:generate go run github.com/princjef/gomarkdoc/cmd/gomarkdoc@v1.1.0 --repository.url https://github.com/yeixio/toskar-sdks --repository.default-branch main --repository.path /go/ --output ../reference/go/README.md .
//go:generate go run github.com/princjef/gomarkdoc/cmd/gomarkdoc@v1.1.0 --repository.url https://github.com/yeixio/toskar-sdks --repository.default-branch main --repository.path /go/ --output ../reference/go/discover.md ./discover
