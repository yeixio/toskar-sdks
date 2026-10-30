using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Text.Json;

namespace Toskar;

// The generated half of this class (Generated/ToskarApi.cs) calls these.
public sealed partial class ToskarApi
{
    private static readonly string[] NoParams = Array.Empty<string>();
    private static readonly (string, object?)[] NoPairs = Array.Empty<(string, object?)>();

    private readonly ToskarClient client;

    internal ToskarApi(ToskarClient client) => this.client = client;

    private static HttpContent Json<T>(T body) => ToskarClient.JsonContent(body);

    private static HttpContent? Raw(object? body, string media) => body switch
    {
        null => null,
        byte[] bytes => new ByteArrayContent(bytes) { Headers = { ContentType = new(media) } },
        _ => new StringContent(body.ToString() ?? "", System.Text.Encoding.UTF8, media),
    };
}
