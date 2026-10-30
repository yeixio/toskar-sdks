using System;
using System.Globalization;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text.RegularExpressions;

namespace Toskar;

/// <summary>How the SDK reads and writes Core's JSON.</summary>
internal static class CoreJson
{
    /// <summary>
    /// A newer Core's fields are passed over, not failed on, and unset fields
    /// stay out of requests.
    /// </summary>
    internal static readonly JsonSerializerOptions Options = new()
    {
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
        Converters = { new CoreTime() },
    };
}

/// <summary>
/// Core's times: RFC 3339 with up to nanoseconds, as Go writes them. .NET
/// reads at most 7 fraction digits, so the rest are dropped.
/// </summary>
internal sealed partial class CoreTime : JsonConverter<DateTimeOffset>
{
    [GeneratedRegex(@"(\.\d{7})\d+")]
    private static partial Regex Nanos();

    public override DateTimeOffset Read(ref Utf8JsonReader reader, Type typeToConvert, JsonSerializerOptions options) =>
        DateTimeOffset.Parse(Nanos().Replace(reader.GetString() ?? "", "$1"), CultureInfo.InvariantCulture, DateTimeStyles.RoundtripKind);

    public override void Write(Utf8JsonWriter writer, DateTimeOffset value, JsonSerializerOptions options) =>
        writer.WriteStringValue(value.ToString("O", CultureInfo.InvariantCulture));
}
