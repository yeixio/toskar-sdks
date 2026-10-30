//! Address records: how a paired device finds its computer away from home
//! (Toskar Core's docs/connecting.md). A record is sealed with the route
//! secret only the computer and its paired devices have, and signed by the
//! computer's own certificate, so a relay that keeps it can neither read it
//! nor change it.

use std::time::Duration;

use aws_lc_rs::aead::{AES_256_GCM, Aad, LessSafeKey, Nonce, UnboundKey};
use aws_lc_rs::{digest, hkdf};
use base64::Engine;
use base64::engine::general_purpose::{STANDARD, URL_SAFE_NO_PAD};
use rustls::pki_types::CertificateDer;
use serde::Deserialize;
use time::OffsetDateTime;

use crate::{Error, Result};

/// What an address record says: the computer's ways in, and when it wrote them.
#[derive(Clone, Debug, PartialEq)]
pub struct AddressRecord {
    /// The ways in, host:port.
    pub addresses: Vec<String>,
    /// When the computer wrote the record.
    pub at: OffsetDateTime,
}

/// The route ID a route secret names.
pub fn route_id(secret: &str) -> Result<String> {
    Ok(lower_base32(&hkdf_sha256(
        &route_secret(secret)?,
        "toskar route id",
        20,
    )))
}

/// The pin of a certificate: "sha256:<hex>" of its DER.
pub fn pin_of(der: &[u8]) -> String {
    let hash = digest::digest(&digest::SHA256, der);
    let hex: String = hash.as_ref().iter().map(|b| format!("{b:02x}")).collect();
    format!("sha256:{hex}")
}

/// How a pin is shown for the person to compare: its first 8 hex digits, as ABCD-1234.
pub fn short_pin(pin: &str) -> String {
    let hex = pin.strip_prefix("sha256:").unwrap_or(pin).to_uppercase();
    if hex.len() < 8 {
        hex
    } else {
        format!("{}-{}", &hex[..4], &hex[4..8])
    }
}

#[derive(Deserialize)]
struct Signed {
    payload: String,
    cert: String,
    alg: String,
    sig: String,
}

#[derive(Deserialize)]
struct Body {
    v: i64,
    route: String,
    at: i64,
    addresses: Vec<String>,
}

/// Opens an address record as docs/connecting.md says: sealed with the
/// route secret, from the certificate with pin, for this route, written at
/// most max_age before now. It answers an [`Error`] with `RECORD_SEALED`,
/// `RECORD_PIN`, or `RECORD_STALE` otherwise.
pub fn open(blob: &[u8], secret: &str, pin: &str, now: OffsetDateTime, max_age: Duration) -> Result<AddressRecord> {
    let route = route_id(secret)?;
    let key = hkdf_sha256(&route_secret(secret)?, "toskar route key", 32);
    let sealed = || Error::new(0, "RECORD_SEALED", "The record doesn't open with this route secret");
    // The nonce, then the sealed record and its tag.
    if blob.len() < 12 + 16 {
        return Err(sealed());
    }
    let key = LessSafeKey::new(UnboundKey::new(&AES_256_GCM, &key).map_err(|_| sealed())?);
    let nonce = Nonce::try_assume_unique_for_key(&blob[..12]).map_err(|_| sealed())?;
    let mut in_out = blob[12..].to_vec();
    let plain = key
        .open_in_place(nonce, Aad::from(route.as_bytes()), &mut in_out)
        .map_err(|_| sealed())?;
    let signed: Signed = serde_json::from_slice(plain).map_err(|_| sealed())?;

    let from_pinned = || Error::new(0, "RECORD_PIN", "The record isn't from the pinned computer");
    let payload = STANDARD.decode(&signed.payload).map_err(|_| from_pinned())?;
    let cert = STANDARD.decode(&signed.cert).map_err(|_| from_pinned())?;
    let sig = STANDARD.decode(&signed.sig).map_err(|_| from_pinned())?;
    if !pin_of(&cert).eq_ignore_ascii_case(pin) || !verify(&sig, &payload, &signed.alg, &cert) {
        return Err(from_pinned());
    }
    let body: Body = serde_json::from_slice(&payload).map_err(|_| from_pinned())?;
    if body.v != 1 || body.route != route {
        return Err(from_pinned());
    }
    let at = OffsetDateTime::from_unix_timestamp(body.at).map_err(|_| from_pinned())?;
    if now - at > max_age || at - now > Duration::from_secs(5 * 60) {
        return Err(Error::new(0, "RECORD_STALE", "The record is too old"));
    }
    Ok(AddressRecord {
        addresses: body.addresses,
        at,
    })
}

pub(crate) fn route_secret(secret: &str) -> Result<Vec<u8>> {
    URL_SAFE_NO_PAD
        .decode(secret.trim_end_matches('='))
        .ok()
        .filter(|s| s.len() == 32)
        .ok_or_else(|| Error::new(0, "BAD_ROUTE_SECRET", "A route secret is 32 bytes, base64url"))
}

struct Len(usize);

impl hkdf::KeyType for Len {
    fn len(&self) -> usize {
        self.0
    }
}

/// HKDF-SHA256 with no salt (RFC 5869).
pub(crate) fn hkdf_sha256(secret: &[u8], info: &str, length: usize) -> Vec<u8> {
    let mut out = vec![0; length];
    let info = [info.as_bytes()];
    hkdf::Salt::new(hkdf::HKDF_SHA256, &[])
        .extract(secret)
        .expand(&info, Len(length))
        .and_then(|okm| okm.fill(&mut out))
        .expect("HKDF-SHA256 makes up to 8160 bytes");
    out
}

/// RFC 4648 base32 in lower case, without padding, as route IDs are.
fn lower_base32(data: &[u8]) -> String {
    const ALPHABET: &[u8] = b"abcdefghijklmnopqrstuvwxyz234567";
    let mut out = String::new();
    let (mut buffer, mut bits) = (0u32, 0);
    for &b in data {
        buffer = (buffer << 8) | u32::from(b);
        bits += 8;
        while bits >= 5 {
            out.push(ALPHABET[((buffer >> (bits - 5)) & 31) as usize] as char);
            bits -= 5;
        }
    }
    if bits > 0 {
        out.push(ALPHABET[((buffer << (5 - bits)) & 31) as usize] as char);
    }
    out
}

/// Whether sig signs payload with the key in cert, by alg: ECDSA P-256 and
/// RSA PKCS #1 v1.5 with SHA-256, and Ed25519.
fn verify(sig: &[u8], payload: &[u8], alg: &str, cert: &[u8]) -> bool {
    let algorithm = match alg {
        "ecdsa-sha256" => webpki::aws_lc_rs::ECDSA_P256_SHA256,
        "rsa-pkcs1-sha256" => webpki::aws_lc_rs::RSA_PKCS1_2048_8192_SHA256,
        "ed25519" => webpki::aws_lc_rs::ED25519,
        _ => return false,
    };
    let der = CertificateDer::from(cert);
    webpki::EndEntityCert::try_from(&der)
        .and_then(|ee| ee.verify_signature(algorithm, payload, sig))
        .is_ok()
}
