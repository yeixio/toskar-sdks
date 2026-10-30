package ai.toskar

import java.time.Instant
import java.time.OffsetDateTime
import kotlinx.serialization.KSerializer
import kotlinx.serialization.descriptors.PrimitiveKind
import kotlinx.serialization.descriptors.PrimitiveSerialDescriptor
import kotlinx.serialization.encoding.Decoder
import kotlinx.serialization.encoding.Encoder

/**
 * Core's times: RFC 3339, with up to nanoseconds and any offset, as Go
 * writes them.
 */
internal object CoreInstant : KSerializer<Instant> {
    override val descriptor = PrimitiveSerialDescriptor("ai.toskar.CoreInstant", PrimitiveKind.STRING)

    override fun deserialize(decoder: Decoder): Instant = OffsetDateTime.parse(decoder.decodeString()).toInstant()

    override fun serialize(encoder: Encoder, value: Instant) = encoder.encodeString(value.toString())
}
