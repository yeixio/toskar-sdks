// Runs the shared conformance cases (conformance/README.md) with the .NET
// SDK. It prints one line of JSON and exits 0, or prints
// {"error": {"code", "message"}} and exits 1.

using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using Toskar;
using Toskar.Models;

const string Usage = "usage: toskar-conformance pair <address> <code> | call <device.json> | chat|stream <model> <message> | events <model> <message> <until> | upload <file> | download <id>";

try
{
    Console.WriteLine((await Run(args)).ToJsonString());
    return 0;
}
catch (ToskarException e)
{
    // With the inner exception, such as a certificate the relay showed: a test bed's log then says why.
    var message = e.Message + (e.InnerException is { } inner ? $": {inner.Message}" : "");
    Console.WriteLine(new JsonObject { ["error"] = new JsonObject { ["code"] = e.Code, ["message"] = message } }.ToJsonString());
    return 1;
}
catch (Exception e)
{
    Console.WriteLine(new JsonObject { ["error"] = new JsonObject { ["code"] = "ERROR", ["message"] = e.ToString() } }.ToJsonString());
    return 1;
}

static async Task<JsonNode> Run(string[] args)
{
    switch (args)
    {
        case ["pair", var address, var code]:
        {
            var shown = "";
            var device = await ToskarClient.PairAsync(address, code, ".NET conformance", s => { shown = s; return true; });
            return new JsonObject { ["device"] = JsonSerializer.SerializeToNode(device), ["short_pin"] = shown };
        }
        case ["call", var file]:
        {
            var device = JsonSerializer.Deserialize<Device>(await File.ReadAllTextAsync(file))!;
            using var toskar = new ToskarClient(device, new ToskarOptions { Retries = 0 });
            var settings = await toskar.Api.GetSettingsAsync();
            return new JsonObject
            {
                ["path"] = toskar.Path?.ToString().ToLowerInvariant() ?? "",
                ["node_name"] = settings["node_name"]?.GetValue<string>() ?? "",
            };
        }
    }
    // The rest connect as TOSKAR_URL and TOSKAR_API_KEY say.
    using var client = new ToskarClient(new ToskarOptions { Retries = 0 });
    switch (args)
    {
        case ["chat", var model, var message]:
            return new JsonObject { ["content"] = (await client.ChatAsync(new ChatRequest { Message = message, ModelId = model })).Content };
        case ["stream", var model, var message]:
        {
            var content = new StringBuilder();
            var tokens = 0;
            var done = false;
            await foreach (var e in client.ChatStreamAsync(new ChatRequest { Message = message, ModelId = model }))
            {
                switch (e)
                {
                    case ChatEvent.Token t:
                        tokens++;
                        content.Append(t.Text);
                        break;
                    case ChatEvent.Done:
                        done = true;
                        break;
                }
            }
            return new JsonObject { ["content"] = content.ToString(), ["tokens"] = tokens, ["done"] = done };
        }
        case ["events", var model, var message, var until]:
            return await Events(client, model, message, until);
        case ["upload", var file]:
        {
            var up = await client.Api.UploadArtifactAsync(new UploadArtifactRequest
            {
                Name = Path.GetFileName(file),
                ContentBase64 = Convert.ToBase64String(await File.ReadAllBytesAsync(file)),
            });
            return new JsonObject { ["id"] = up.Id, ["name"] = up.Name, ["size_bytes"] = up.SizeBytes };
        }
        case ["download", var id]:
        {
            var data = await client.Api.GetArtifactContentAsync(id);
            return new JsonObject { ["sha256"] = Convert.ToHexString(SHA256.HashData(data)).ToLowerInvariant(), ["size_bytes"] = data.Length };
        }
        default:
            throw new ToskarException(0, "ERROR", Usage);
    }
}

// Listens to the events stream, asks once, and lists the events' types until one of type until.
static async Task<JsonNode> Events(ToskarClient toskar, string model, string message, string until)
{
    using var listening = new CancellationTokenSource(TimeSpan.FromSeconds(30));
    var types = new JsonArray();
    var listen = Task.Run(async () =>
    {
        await foreach (var e in toskar.EventsAsync(listening.Token))
        {
            types.Add(e.Type);
            if (e.Type == until)
            {
                break;
            }
        }
    });
    // Time to subscribe before asking.
    await Task.Delay(1000);
    await toskar.ChatAsync(new ChatRequest { Message = message, ModelId = model });
    await listen;
    return new JsonObject { ["types"] = types };
}
