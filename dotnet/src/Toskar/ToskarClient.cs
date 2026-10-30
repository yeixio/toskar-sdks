// The .NET SDK for Toskar: local AI across your own computers.
//
//     using var toskar = new ToskarClient();
//     await foreach (var e in toskar.ChatStreamAsync(new ChatRequest { Message = "Hi" }))
//         if (e is ChatEvent.Token t) Console.Write(t.Text);
//
// Api reaches every route, typed from Toskar Core's API spec:
//
//     var models = await toskar.Api.ListModelsAsync();

using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Runtime.CompilerServices;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Toskar.Models;

namespace Toskar;

/// <summary>How to connect: every setting has a default.</summary>
public sealed record ToskarOptions
{
    /// <summary>Where Toskar Core answers. Default: <c>TOSKAR_URL</c>, or <see cref="ToskarClient.DefaultUrl"/>, this computer.</summary>
    public string? Url { get; init; }

    /// <summary>The API key for any address other than this computer's loopback. Default: <c>TOSKAR_API_KEY</c>.</summary>
    public string? Key { get; init; }

    /// <summary>
    /// How many times a safe request (GET, HEAD, OPTIONS) that fails to
    /// connect or answers 502, 503, or 504 is retried. A chat is never
    /// retried: it could answer twice.
    /// </summary>
    public int Retries { get; init; } = 2;

    /// <summary>How long to wait for an answer to start. A streamed answer then runs for as long as it takes.</summary>
    public TimeSpan Timeout { get; init; } = TimeSpan.FromSeconds(60);

    /// <summary>The HttpClient to send requests with, in place of one the client makes. The client doesn't dispose it.</summary>
    public HttpClient? HttpClient { get; init; }

    /// <summary>Headers to add to every request.</summary>
    public IReadOnlyDictionary<string, string>? Headers { get; init; }
}

/// <summary>
/// A connection to Toskar Core. Dispose it when you're done, to free its
/// connections.
/// </summary>
public sealed class ToskarClient : IDisposable
{
    /// <summary>This computer's Toskar Core, which needs no key.</summary>
    public const string DefaultUrl = "http://127.0.0.1:7331";

    private static readonly HashSet<string> Safe = new() { "GET", "HEAD", "OPTIONS" };
    private static readonly HashSet<int> Retried = new() { 502, 503, 504 };

    /// <summary>The most of an error answer read; Core's are small.</summary>
    private const int ErrorLimit = 1 << 20;

    private readonly Uri baseUri;
    private readonly List<KeyValuePair<string, string>> sent;
    private readonly int retries;
    private readonly TimeSpan timeout;
    private readonly HttpClient http;
    private readonly bool ownsClient;

    /// <summary>Connects to Toskar Core: this computer's, unless options or <c>TOSKAR_URL</c> say another.</summary>
    public ToskarClient(ToskarOptions? options = null)
        : this(options ?? new ToskarOptions(), Environment.GetEnvironmentVariable)
    {
    }

    /// <summary>Connects to the Toskar Core at url, with key for any address other than this computer's loopback.</summary>
    public ToskarClient(string url, string? key = null)
        : this(new ToskarOptions { Url = url, Key = key })
    {
    }

    internal ToskarClient(ToskarOptions options, Func<string, string?> env)
    {
        var raw = (NotEmpty(options.Url) ?? NotEmpty(env("TOSKAR_URL")) ?? DefaultUrl).TrimEnd('/');
        if (!Uri.TryCreate(raw + "/", UriKind.Absolute, out var parsed) || (parsed.Scheme != "http" && parsed.Scheme != "https"))
        {
            throw new ToskarException(0, "BAD_URL", $"{raw} isn't an http or https address");
        }
        baseUri = parsed;
        Url = raw;
        sent = new()
        {
            // Core answers 426 CONTRACT_MISMATCH to a client of another major version.
            new("Toskar-Client-Contract", Contract.Version),
        };
        if ((NotEmpty(options.Key) ?? NotEmpty(env("TOSKAR_API_KEY"))) is { } key)
        {
            sent.Add(new("Authorization", $"Bearer {key}"));
        }
        foreach (var (name, value) in (options.Headers ?? new Dictionary<string, string>()).OrderBy(h => h.Key, StringComparer.Ordinal))
        {
            sent.Add(new(name, value));
        }
        retries = Math.Max(0, options.Retries);
        timeout = options.Timeout;
        ownsClient = options.HttpClient is null;
        // The client's own timeout would end a long stream: each call has its own instead.
        http = options.HttpClient ?? new HttpClient { Timeout = System.Threading.Timeout.InfiniteTimeSpan };
        Api = new ToskarApi(this);
    }

    /// <summary>Where Toskar Core answers.</summary>
    public string Url { get; }

    /// <summary>Every route, typed from Toskar Core's API spec.</summary>
    public ToskarApi Api { get; }

    /// <summary>Asks once and waits for the whole answer.</summary>
    public Task<ChatAnswer> ChatAsync(ChatRequest request, CancellationToken cancellationToken = default) =>
        Api.ChatAsync(request with { Stream = false }, cancellationToken);

    /// <summary>
    /// Asks and yields the answer as it's written: tokens, then done. A
    /// failure throws a <see cref="ToskarException"/> with its code, such as
    /// <see cref="ErrorCodes.NO_MODEL_INSTALLED"/>, and ends the stream.
    /// </summary>
    public async IAsyncEnumerable<ChatEvent> ChatStreamAsync(
        ChatRequest request, [EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        using var response = await SendRawAsync(
            "POST", "/api/v1/chat", Array.Empty<string>(), Array.Empty<(string, object?)>(), Array.Empty<(string, object?)>(),
            JsonContent(request with { Stream = true }), "text/event-stream", stream: true, cancellationToken).ConfigureAwait(false);
        await foreach (var e in ServerSentEvents.ReadAsync(response, cancellationToken).ConfigureAwait(false))
        {
            switch (e.Name)
            {
                case "token":
                    yield return new ChatEvent.Token(JsonSerializer.Deserialize<ChatToken>(e.Data, CoreJson.Options)!.Content);
                    break;
                case "done":
                    ChatDone? done = null;
                    try
                    {
                        done = JsonSerializer.Deserialize<ChatDone>(e.Data, CoreJson.Options);
                    }
                    catch (JsonException)
                    {
                    }
                    yield return new ChatEvent.Done(done?.Metrics);
                    yield break;
                case "error_code":
                    throw ToskarException.Of(200, e.Data);
                case "error":
                    throw new ToskarException(200, ErrorCodes.CHAT_FAILED, e.Data.Length > 0 ? e.Data : "The chat failed");
            }
        }
        // Every stream ends with done or an error, so one that just stops was cut off.
        throw new ToskarException(200, "CONNECTION_LOST", "The answer stopped before it finished");
    }

    /// <summary>
    /// Yields what happens on Toskar as it happens, such as models loading
    /// and automations running, until you cancel.
    /// </summary>
    public async IAsyncEnumerable<Event> EventsAsync([EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        using var response = await SendRawAsync(
            "GET", "/api/v1/events", Array.Empty<string>(), Array.Empty<(string, object?)>(), Array.Empty<(string, object?)>(),
            null, "text/event-stream", stream: true, cancellationToken).ConfigureAwait(false);
        await foreach (var e in ServerSentEvents.ReadAsync(response, cancellationToken).ConfigureAwait(false))
        {
            if (e.Data.Length > 0)
            {
                yield return JsonSerializer.Deserialize<Event>(e.Data, CoreJson.Options)!;
            }
        }
    }

    /// <summary>Core's version and its client contract.</summary>
    public Task<VersionResponse> VersionAsync(CancellationToken cancellationToken = default) =>
        Api.GetVersionAsync(cancellationToken);

    /// <summary>Frees the connections, unless the HttpClient was given.</summary>
    public void Dispose()
    {
        if (ownsClient)
        {
            http.Dispose();
        }
    }

    // The generated ToskarApi calls these.

    internal async Task<T> CallAsync<T>(
        string method, string path, string[] parameters, (string, object?)[] query, (string, object?)[] headers,
        HttpContent? body, CancellationToken cancellationToken)
    {
        using var response = await SendRawAsync(method, path, parameters, query, headers, body, "application/json", stream: false, cancellationToken)
            .ConfigureAwait(false);
        var text = await response.Content.ReadAsStringAsync(cancellationToken).ConfigureAwait(false);
        return JsonSerializer.Deserialize<T>(text, CoreJson.Options)!;
    }

    internal async Task<byte[]> BytesAsync(
        string method, string path, string[] parameters, (string, object?)[] query, (string, object?)[] headers,
        HttpContent? body, CancellationToken cancellationToken)
    {
        using var response = await SendRawAsync(method, path, parameters, query, headers, body, "*/*", stream: false, cancellationToken)
            .ConfigureAwait(false);
        return await response.Content.ReadAsByteArrayAsync(cancellationToken).ConfigureAwait(false);
    }

    internal async Task SendAsync(
        string method, string path, string[] parameters, (string, object?)[] query, (string, object?)[] headers,
        HttpContent? body, CancellationToken cancellationToken)
    {
        using var response = await SendRawAsync(method, path, parameters, query, headers, body, "*/*", stream: false, cancellationToken)
            .ConfigureAwait(false);
    }

    internal static HttpContent JsonContent<T>(T body) =>
        new StringContent(JsonSerializer.Serialize(body, CoreJson.Options), Encoding.UTF8, "application/json");

    /// <summary>
    /// Sends a request, retrying a safe one, and throws a
    /// <see cref="ToskarException"/> for an error answer. The caller disposes
    /// the response.
    /// </summary>
    internal async Task<HttpResponseMessage> SendRawAsync(
        string method, string path, string[] parameters, (string, object?)[] query, (string, object?)[] headers,
        HttpContent? body, string accept, bool stream, CancellationToken cancellationToken)
    {
        var target = Target(path, parameters, query);
        // A request's body can be sent once, so a retry sends a copy.
        var bytes = body is null ? null : await body.ReadAsByteArrayAsync(cancellationToken).ConfigureAwait(false);
        var attempts = Safe.Contains(method) ? 1 + retries : 1;
        for (var attempt = 1; ; attempt++)
        {
            using var request = new HttpRequestMessage(new HttpMethod(method), target);
            foreach (var (name, value) in sent)
            {
                request.Headers.TryAddWithoutValidation(name, value);
            }
            foreach (var (name, value) in headers)
            {
                if (value is not null)
                {
                    request.Headers.TryAddWithoutValidation(name, value.ToString());
                }
            }
            request.Headers.Accept.Add(new MediaTypeWithQualityHeaderValue(accept));
            if (bytes is not null)
            {
                request.Content = new ByteArrayContent(bytes);
                request.Content.Headers.ContentType = body!.Headers.ContentType;
            }
            // Waiting for the answer to start has the timeout; a stream then runs on.
            using var started = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
            if (timeout > TimeSpan.Zero)
            {
                started.CancelAfter(timeout);
            }
            HttpResponseMessage? response = null;
            try
            {
                response = await http.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, started.Token).ConfigureAwait(false);
                if (!stream)
                {
                    await response.Content.LoadIntoBufferAsync().WaitAsync(started.Token).ConfigureAwait(false);
                }
            }
            catch (Exception e) when (e is HttpRequestException || (e is OperationCanceledException && !cancellationToken.IsCancellationRequested))
            {
                response?.Dispose();
                if (attempt >= attempts)
                {
                    var why = e is OperationCanceledException ? $"no answer within {timeout.TotalSeconds:0.#} s" : e.Message;
                    throw new ToskarException(0, "CONNECTION_FAILED", $"Couldn't reach Toskar at {Url}: {why}", inner: e);
                }
                await Backoff(attempt, cancellationToken).ConfigureAwait(false);
                continue;
            }
            var code = (int)response.StatusCode;
            if (code < 300)
            {
                return response;
            }
            if (attempt >= attempts || !Retried.Contains(code))
            {
                using (response)
                {
                    var text = await ReadLimited(response, cancellationToken).ConfigureAwait(false);
                    throw ToskarException.Of(code, text);
                }
            }
            response.Dispose();
            await Backoff(attempt, cancellationToken).ConfigureAwait(false);
        }
    }

    private Uri Target(string path, string[] parameters, (string, object?)[] query)
    {
        var next = 0;
        var segments = path.Split('/', StringSplitOptions.RemoveEmptyEntries)
            .Select(s => s.StartsWith('{') ? Uri.EscapeDataString(parameters[next++]) : s);
        var builder = new StringBuilder(baseUri.AbsolutePath.TrimEnd('/'));
        foreach (var s in segments)
        {
            builder.Append('/').Append(s);
        }
        var pairs = new List<string>();
        foreach (var (name, value) in query)
        {
            switch (value)
            {
                case null:
                    break;
                case string text:
                    pairs.Add($"{Uri.EscapeDataString(name)}={Uri.EscapeDataString(text)}");
                    break;
                case bool flag:
                    pairs.Add($"{Uri.EscapeDataString(name)}={(flag ? "true" : "false")}");
                    break;
                case System.Collections.IEnumerable many:
                    foreach (var item in many)
                    {
                        pairs.Add($"{Uri.EscapeDataString(name)}={Uri.EscapeDataString(Convert.ToString(item, System.Globalization.CultureInfo.InvariantCulture) ?? "")}");
                    }
                    break;
                default:
                    pairs.Add($"{Uri.EscapeDataString(name)}={Uri.EscapeDataString(Convert.ToString(value, System.Globalization.CultureInfo.InvariantCulture) ?? "")}");
                    break;
            }
        }
        var uri = new UriBuilder(baseUri) { Path = builder.ToString(), Query = string.Join("&", pairs) };
        return uri.Uri;
    }

    private static async Task<string> ReadLimited(HttpResponseMessage response, CancellationToken cancellationToken)
    {
        await using var body = await response.Content.ReadAsStreamAsync(cancellationToken).ConfigureAwait(false);
        var buffer = new byte[ErrorLimit];
        var read = 0;
        int n;
        while (read < buffer.Length && (n = await body.ReadAsync(buffer.AsMemory(read), cancellationToken).ConfigureAwait(false)) > 0)
        {
            read += n;
        }
        return Encoding.UTF8.GetString(buffer, 0, read);
    }

    private static Task Backoff(int attempt, CancellationToken cancellationToken) =>
        Task.Delay((200 << (attempt - 1)) + Random.Shared.Next(100), cancellationToken);

    private static string? NotEmpty(string? s) => string.IsNullOrEmpty(s) ? null : s;
}

/// <summary>Reads server-sent events from a response, one at a time.</summary>
internal static class ServerSentEvents
{
    internal readonly record struct Message(string Name, string Data);

    internal static async IAsyncEnumerable<Message> ReadAsync(
        HttpResponseMessage response, [EnumeratorCancellation] CancellationToken cancellationToken)
    {
        await using var body = await response.Content.ReadAsStreamAsync(cancellationToken).ConfigureAwait(false);
        using var reader = new StreamReader(body, Encoding.UTF8);
        var name = "message";
        var data = new StringBuilder();
        var any = false;
        while (true)
        {
            string? line;
            try
            {
                line = await reader.ReadLineAsync(cancellationToken).ConfigureAwait(false);
            }
            catch (IOException e)
            {
                throw new ToskarException(200, "CONNECTION_LOST", "The answer stopped before it finished", inner: e);
            }
            if (line is null)
            {
                if (any)
                {
                    yield return new Message(name, data.ToString());
                }
                yield break;
            }
            if (line.Length == 0)
            {
                if (any)
                {
                    yield return new Message(name, data.ToString());
                    name = "message";
                    data.Clear();
                    any = false;
                }
                continue;
            }
            if (line.StartsWith(':'))
            {
                continue;
            }
            var colon = line.IndexOf(':');
            var field = colon < 0 ? line : line[..colon];
            var value = colon < 0 ? "" : line[(colon + 1)..];
            if (value.StartsWith(' '))
            {
                value = value[1..];
            }
            if (field == "event")
            {
                name = value;
                any = true;
            }
            else if (field == "data")
            {
                if (data.Length > 0)
                {
                    data.Append('\n');
                }
                data.Append(value);
                any = true;
            }
        }
    }
}
