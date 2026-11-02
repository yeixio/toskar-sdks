using Toskar.Models;

namespace Toskar;

/// <summary>One event of a streamed chat: a <see cref="Token"/> or a <see cref="Replace"/>, then <see cref="Done"/>.</summary>
public abstract record ChatEvent
{
    private ChatEvent()
    {
    }

    /// <summary>The next piece of the answer.</summary>
    public sealed record Token(string Text) : ChatEvent;

    /// <summary>With <c>Live</c>: takes the place of everything so far, empty to take it all back.</summary>
    public sealed record Replace(string Text) : ChatEvent;

    /// <summary>The answer is finished and saved, with what the runtime measured when it reported it.</summary>
    public sealed record Done(GenerationMetrics? Metrics) : ChatEvent;
}
