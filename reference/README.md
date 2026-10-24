# Reference

Every class, function, and type each SDK has, generated from its code's doc comments. CI checks they match the code.

| SDK | Reference |
| --- | --- |
| TypeScript and JavaScript | [typescript/](typescript/README.md): [`toskar`](typescript/index.md), and [`toskar/node`](typescript/node.md) for pairing and discovery |
| Python | [python/](python/README.md), with [every route on `toskar.api`](python/api.md) and [the error codes](python/errors.md) |
| Go | [go/](go/README.md), and [`discover`](go/discover.md); also on [pkg.go.dev](https://pkg.go.dev/github.com/yeixio/toskar-sdks/go) |

The routes themselves, with every field: [toskar.ai/developers/api](https://toskar.ai/developers/api).

Regenerate them after changing an SDK:

```sh
(cd typescript && npm run reference)
(cd python && python scripts/reference.py)
(cd go && go generate ./...)
```
