using System;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace Toskar;

/// <summary>
/// An error from Toskar Core: <c>{"error": {"code", "message", "details"}}</c>.
/// <see cref="Code"/> is stable, such as <see cref="ErrorCodes.NO_MODEL_INSTALLED"/>;
/// <see cref="Exception.Message"/> is English text for logs; <see cref="Details"/>
/// has the values the message needs.
/// </summary>
/// <remarks>
/// The SDK's own codes, for what goes wrong before Toskar Core answers, are
/// <c>CONNECTION_FAILED</c> (with the cause as the inner exception),
/// <c>CONNECTION_LOST</c> (a stream cut off), <c>BAD_URL</c>, and
/// <c>HTTP_&lt;status&gt;</c> for an answer that isn't Toskar's.
/// </remarks>
public sealed class ToskarException : Exception
{
    /// <summary>An error with its code.</summary>
    public ToskarException(int status, string code, string message, JsonObject? details = null, Exception? inner = null)
        : base(message, inner)
    {
        Status = status;
        Code = code;
        Details = details;
    }

    /// <summary>The HTTP status Toskar answered with, or 0 when it didn't answer.</summary>
    public int Status { get; }

    /// <summary>The error's code, such as <c>NO_MODEL_INSTALLED</c>.</summary>
    public string Code { get; }

    /// <summary>The values the message needs, when Toskar sent them.</summary>
    public JsonObject? Details { get; }

    /// <summary>The message, status, and code, for logs, such as <c>toskar: No such model (404 MODEL_NOT_FOUND)</c>.</summary>
    public override string ToString() => $"toskar: {Message} ({Status} {Code})";

    /// <summary>The error a response body describes, or a generic one for a body that isn't Toskar's.</summary>
    internal static ToskarException Of(int status, string body)
    {
        try
        {
            var root = JsonNode.Parse(body) as JsonObject;
            // A stream's error_code event is the inner object itself.
            var e = root?["error"] as JsonObject ?? root;
            if (e?["code"] is JsonValue code && code.TryGetValue(out string? text) && !string.IsNullOrEmpty(text))
            {
                var message = e["message"] is JsonValue m && m.TryGetValue(out string? said) ? said : text;
                return new ToskarException(status, text, message, e["details"] as JsonObject);
            }
        }
        catch (JsonException)
        {
        }
        return new ToskarException(status, $"HTTP_{status}", $"Toskar answered {status}");
    }
}
