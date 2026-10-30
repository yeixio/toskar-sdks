using System;
using System.Collections.Generic;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Toskar.Models;
using Xunit;

namespace Toskar.Tests;

/// <summary>Answers requests from a list, and keeps what it was sent.</summary>
internal sealed class FakeCore : HttpMessageHandler
{
    internal sealed record Answer(int Status = 200, string Body = "", string Type = "application/json", bool Fails = false);

    private readonly Queue<Answer> answers;

    internal FakeCore(params Answer[] answers) => this.answers = new(answers);

    internal List<(HttpRequestMessage Request, string? Body)> Sent { get; } = new();

    protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
    {
        var body = request.Content is null ? null : await request.Content.ReadAsStringAsync(cancellationToken);
        Sent.Add((request, body));
        var a = answers.Dequeue();
        if (a.Fails)
        {
            throw new HttpRequestException("connection refused");
        }
        return new HttpResponseMessage((HttpStatusCode)a.Status) { Content = new StringContent(a.Body, Encoding.UTF8, a.Type) };
    }
}

public class ClientTests
{
    internal const string Version = """{"version":"1.12.0","contract":{"version":"1.60","major":1},"commit":"abc","build_date":"2026-10-29","license":"AGPL-3.0","product":"Toskar","source":"https://github.com/yeixio/toskar-core"}""";
    private const string Sse = "text/event-stream";

    private static ToskarClient Toskar(FakeCore core, int retries = 2, string? key = null) =>
        new(new ToskarOptions { Url = "http://core.test:7331", Key = key, Retries = retries, HttpClient = new HttpClient(core) }, _ => null);

    [Fact]
    public async Task SaysItsContractAndSendsTheKey()
    {
        var core = new FakeCore(new FakeCore.Answer(Body: Version));
        Assert.Equal("1.12.0", (await Toskar(core, key: "secret").VersionAsync()).Version);
        var r = core.Sent[0].Request;
        Assert.Equal(Contract.Version, r.Headers.GetValues("Toskar-Client-Contract").Single());
        Assert.Equal("Bearer secret", r.Headers.Authorization?.ToString());
        Assert.Equal("/api/v1/version", r.RequestUri!.AbsolutePath);
    }

    [Fact]
    public async Task ReadsTheAddressAndKeyFromTheEnvironment()
    {
        var env = new Dictionary<string, string> { ["TOSKAR_URL"] = "http://studio.test:7331/", ["TOSKAR_API_KEY"] = "env" };
        var core = new FakeCore(new FakeCore.Answer(Body: Version));
        var toskar = new ToskarClient(new ToskarOptions { HttpClient = new HttpClient(core) }, k => env.GetValueOrDefault(k));
        await toskar.VersionAsync();
        Assert.Equal("http://studio.test:7331", toskar.Url);
        Assert.Equal("Bearer env", core.Sent[0].Request.Headers.Authorization?.ToString());
        Assert.Equal(ToskarClient.DefaultUrl, new ToskarClient(new ToskarOptions(), _ => null).Url);
    }

    [Fact]
    public async Task ChatsWaitingForTheWholeAnswer()
    {
        var core = new FakeCore(new FakeCore.Answer(Body: """{"content":"Hello there","metrics":null}"""));
        var answer = await Toskar(core).ChatAsync(new ChatRequest { Message = "Hi" });
        Assert.Equal("Hello there", answer.Content);
        Assert.Equal("application/json", core.Sent[0].Request.Headers.Accept.Single().MediaType);
        // Unset fields stay out of the request, and stream says how it's answered.
        Assert.Equal("""{"message":"Hi","stream":false}""", core.Sent[0].Body);
    }

    [Fact]
    public async Task StreamsAnAnswerAsItIsWritten()
    {
        var body = """
            : ping

            event: token
            data: {"content":"Hel"}

            event: token
            data: {"content":"lo"}

            event: done
            data: {"metrics":{"prompt_tokens":3,"completion_tokens":2,"total_tokens":5,"ttft_ms":1,"prompt_ms":1,"eval_ms":1,"total_ms":2,"prompt_tok_per_sec":3,"eval_tok_per_sec":2}}


            """;
        var core = new FakeCore(new FakeCore.Answer(Body: body, Type: Sse));
        var text = "";
        GenerationMetrics? metrics = null;
        await foreach (var e in Toskar(core).ChatStreamAsync(new ChatRequest { Message = "Hi" }))
        {
            switch (e)
            {
                case ChatEvent.Token t:
                    text += t.Text;
                    break;
                case ChatEvent.Done d:
                    metrics = d.Metrics;
                    break;
            }
        }
        Assert.Equal("Hello", text);
        Assert.Equal(2L, metrics?.CompletionTokens);
        Assert.Equal(Sse, core.Sent[0].Request.Headers.Accept.Single().MediaType);
    }

    [Fact]
    public async Task AStreamedFailureHasItsCode()
    {
        var core = new FakeCore(new FakeCore.Answer(Body: "event: error_code\ndata: {\"code\":\"NO_MODEL_INSTALLED\",\"message\":\"Install a model\"}\n\n", Type: Sse));
        var e = await Assert.ThrowsAsync<ToskarException>(async () =>
        {
            await foreach (var _ in Toskar(core).ChatStreamAsync(new ChatRequest { Message = "Hi" }))
            {
            }
        });
        Assert.Equal(ErrorCodes.NO_MODEL_INSTALLED, e.Code);
        Assert.Equal("Install a model", e.Message);
    }

    [Fact]
    public async Task ACutOffStreamSaysSo()
    {
        var core = new FakeCore(new FakeCore.Answer(Body: "event: token\ndata: {\"content\":\"Hel\"}\n\n", Type: Sse));
        var e = await Assert.ThrowsAsync<ToskarException>(async () =>
        {
            await foreach (var _ in Toskar(core).ChatStreamAsync(new ChatRequest { Message = "Hi" }))
            {
            }
        });
        Assert.Equal("CONNECTION_LOST", e.Code);
    }

    [Fact]
    public async Task AnErrorAnswerIsAToskarException()
    {
        var core = new FakeCore(
            new FakeCore.Answer(404, """{"error":{"code":"MODEL_NOT_FOUND","message":"No such model","details":{"model_id":"x"}}}"""),
            new FakeCore.Answer(500, "oops", "text/plain"));
        var toskar = Toskar(core);
        var e = await Assert.ThrowsAsync<ToskarException>(() => toskar.Api.ListModelsAsync());
        Assert.Equal(404, e.Status);
        Assert.Equal(ErrorCodes.MODEL_NOT_FOUND, e.Code);
        Assert.Equal("No such model", e.Message);
        Assert.Equal("x", e.Details?["model_id"]?.GetValue<string>());
        // A body that isn't Toskar's still says what happened.
        Assert.Equal("HTTP_500", (await Assert.ThrowsAsync<ToskarException>(() => toskar.VersionAsync())).Code);
    }

    [Fact]
    public async Task RetriesASafeRequestButNeverAChat()
    {
        var core = new FakeCore(new FakeCore.Answer(Fails: true), new FakeCore.Answer(503), new FakeCore.Answer(Body: Version));
        await Toskar(core).VersionAsync();
        Assert.Equal(3, core.Sent.Count);

        var busy = new FakeCore(new FakeCore.Answer(503), new FakeCore.Answer(503), new FakeCore.Answer(503), new FakeCore.Answer(Body: Version));
        Assert.Equal(503, (await Assert.ThrowsAsync<ToskarException>(() => Toskar(busy).VersionAsync())).Status);
        Assert.Equal(3, busy.Sent.Count);

        var chat = new FakeCore(new FakeCore.Answer(503), new FakeCore.Answer(Body: """{"content":"twice"}"""));
        Assert.Equal(503, (await Assert.ThrowsAsync<ToskarException>(() => Toskar(chat).ChatAsync(new ChatRequest { Message = "Hi" }))).Status);
        Assert.Single(chat.Sent);
    }

    [Fact]
    public async Task AComputerThatIsntThereSaysSo()
    {
        var core = new FakeCore(new FakeCore.Answer(Fails: true));
        var e = await Assert.ThrowsAsync<ToskarException>(() => Toskar(core, retries: 0).VersionAsync());
        Assert.Equal("CONNECTION_FAILED", e.Code);
        Assert.Equal(0, e.Status);
        Assert.IsType<HttpRequestException>(e.InnerException);
    }

    [Fact]
    public async Task ReadsTheEventsStream()
    {
        var body = """
            data: {"id":"e1","type":"model.loaded","contract":"1.60","timestamp":"2026-10-29T16:04:05.123456789Z","payload":{"model_id":"m1"}}

            data: {"id":"e2","type":"model.unloaded","contract":"1.60","timestamp":"2026-10-29T16:04:06Z","payload":{}}


            """;
        var core = new FakeCore(new FakeCore.Answer(Body: body, Type: Sse));
        var seen = new List<Event>();
        await foreach (var e in Toskar(core).EventsAsync())
        {
            seen.Add(e);
        }
        Assert.Equal(new[] { "model.loaded", "model.unloaded" }, seen.Select(e => e.Type));
        Assert.Equal(new DateTimeOffset(2026, 10, 29, 16, 4, 5, TimeSpan.Zero).AddTicks(1234567), seen[0].Timestamp);
    }

    [Fact]
    public async Task PutsParametersInThePathAndQuery()
    {
        var core = new FakeCore(new FakeCore.Answer(Body: "[]"), new FakeCore.Answer(Body: "{}"));
        var toskar = Toskar(core, retries: 0);
        await toskar.Api.ListModelsAsync();
        await toskar.Api.DeleteMemoryAsync("a/b c");
        var r = core.Sent[1].Request;
        Assert.Equal("DELETE", r.Method.Method);
        Assert.Equal("/api/v1/memory/a%2Fb%20c", r.RequestUri!.AbsolutePath);
    }

    [Fact]
    public void ReadsCoreTimes()
    {
        static DateTimeOffset Read(string text) =>
            System.Text.Json.JsonSerializer.Deserialize<DateTimeOffset>($"\"{text}\"", CoreJson.Options);
        Assert.Equal(1_793_289_845L, Read("2026-10-29T16:04:05Z").ToUnixTimeSeconds());
        Assert.Equal(DateTimeOffset.FromUnixTimeMilliseconds(1_793_318_645_500L), Read("2026-10-29T16:04:05.5-08:00"));
        Assert.ThrowsAny<Exception>(() => Read("yesterday"));
    }

    [Fact]
    public async Task KeepsOutWhatANewerCoreAdds()
    {
        var core = new FakeCore(new FakeCore.Answer(Body: """{"content":"Hi","metrics":null,"new_field":{"a":1}}"""));
        var a = await Toskar(core).ChatAsync(new ChatRequest { Message = "Hi" });
        Assert.Equal("Hi", a.Content);
        Assert.Null(a.Metrics);
    }
}
