//! Pairing, pinning, and address records, against spec/connection-vectors.json
//! and a computer and relay that answer HTTPS on this computer.

use std::sync::{Arc, Mutex};
use std::time::Duration;

use aws_lc_rs::aead::{AES_256_GCM, Aad, LessSafeKey, Nonce, UnboundKey};
use base64::Engine;
use base64::engine::general_purpose::{STANDARD, URL_SAFE_NO_PAD};
use rustls::pki_types::{CertificateDer, PrivateKeyDer, PrivatePkcs8KeyDer};
use serde_json::{Value, json};
use time::OffsetDateTime;
use tokio::io::{AsyncBufReadExt, AsyncReadExt, AsyncWriteExt, BufReader};
use tokio::net::TcpListener;

use crate::connect::{base_of, host_only};
use crate::records::{self, hkdf_sha256, route_secret};
use crate::{Client, ConnectionPath, Device, Route, pair};

fn vectors() -> Value {
    let text =
        std::fs::read_to_string(concat!(env!("CARGO_MANIFEST_DIR"), "/../spec/connection-vectors.json")).unwrap();
    serde_json::from_str(&text).unwrap()
}

#[test]
fn route_ids_are_cores() {
    for r in vectors()["routes"].as_array().unwrap() {
        assert_eq!(records::route_id(r["secret"].as_str().unwrap()).unwrap(), r["route_id"]);
    }
    assert_eq!(records::route_id("too-short").unwrap_err().code, "BAD_ROUTE_SECRET");
}

#[test]
fn pins_are_cores() {
    let v = vectors();
    let pins = v["pins"].as_array().unwrap();
    assert_eq!(pins.len(), 3);
    for p in pins {
        let der = STANDARD.decode(p["cert_der_base64"].as_str().unwrap()).unwrap();
        assert_eq!(records::pin_of(&der), p["fingerprint"]);
        assert_eq!(records::short_pin(p["fingerprint"].as_str().unwrap()), p["short"]);
    }
}

#[test]
fn records_open_as_core_says() {
    for r in vectors()["records"].as_array().unwrap() {
        let name = r["name"].as_str().unwrap();
        let opened = records::open(
            &STANDARD.decode(r["blob_base64"].as_str().unwrap()).unwrap(),
            r["secret"].as_str().unwrap(),
            r["pin"].as_str().unwrap(),
            OffsetDateTime::from_unix_timestamp(r["now"].as_i64().unwrap()).unwrap(),
            Duration::from_secs(r["max_age_seconds"].as_u64().unwrap()),
        );
        match r["error"].as_str() {
            Some(error) => {
                let want = match error {
                    "sealed" => "RECORD_SEALED",
                    "pin" => "RECORD_PIN",
                    _ => "RECORD_STALE",
                };
                assert_eq!(opened.unwrap_err().code, want, "{name}");
            }
            None => {
                let record = opened.unwrap_or_else(|e| panic!("{name}: {e}"));
                assert_eq!(
                    record.addresses,
                    serde_json::from_value::<Vec<String>>(r["addresses"].clone()).unwrap(),
                    "{name}"
                );
                assert_eq!(record.at.unix_timestamp(), r["at"].as_i64().unwrap(), "{name}");
            }
        }
    }
}

#[test]
fn saved_devices_are_the_other_sdks_json() {
    let text = r#"{"address":"192.168.1.20:7331","api_key":"tk_1","pin":"sha256:ab","route":{"secret":"s","id":"i","relay":"relay.toskar.ai","token":"t"}}"#;
    let device: Device = serde_json::from_str(text).unwrap();
    assert_eq!(device.api_key, "tk_1");
    assert_eq!(device.route.as_ref().unwrap().token.as_deref(), Some("t"));
    assert_eq!(serde_json::to_string(&device).unwrap(), text);
    let home_only = Device {
        address: "a:1".into(),
        api_key: "k".into(),
        pin: "p".into(),
        route: None,
    };
    assert_eq!(
        serde_json::to_string(&home_only).unwrap(),
        r#"{"address":"a:1","api_key":"k","pin":"p"}"#
    );
}

#[test]
fn hosts_of_addresses() {
    assert_eq!(host_only("studio.local:7331"), "studio.local");
    assert_eq!(host_only("[fe80::1]:7331"), "fe80::1");
    assert_eq!(host_only("fe80::1"), "fe80::1");
    assert_eq!(host_only("relay.toskar.ai"), "relay.toskar.ai");
    assert_eq!(base_of("nope/path").unwrap_err().code, "BAD_ADDRESS");
}

/// A certificate and its key, as Core makes: ECDSA P-256, self-signed.
struct Held {
    der: CertificateDer<'static>,
    key: Vec<u8>,
}

impl Held {
    fn new(name: &str) -> Self {
        let key = rcgen::KeyPair::generate().unwrap();
        let cert = rcgen::CertificateParams::new(vec![name.into()])
            .unwrap()
            .self_signed(&key)
            .unwrap();
        Self {
            der: cert.der().clone(),
            key: key.serialize_der(),
        }
    }

    fn pin(&self) -> String {
        records::pin_of(&self.der)
    }
}

type Answer = Arc<dyn Fn(&str, Option<&str>) -> (u16, Vec<u8>) + Send + Sync>;

/// What a server was sent: each request's path and authorization.
type Sent = Arc<Mutex<Vec<(String, Option<String>)>>>;

/// A server that answers HTTPS with its own certificate: just enough
/// HTTP/1.1 for a client's requests. It keeps the paths and authorization
/// it was sent.
struct Server {
    address: String,
    sent: Sent,
}

impl Server {
    async fn start(held: &Held, answer: Answer) -> Self {
        let config =
            rustls::ServerConfig::builder_with_provider(Arc::new(rustls::crypto::aws_lc_rs::default_provider()))
                .with_safe_default_protocol_versions()
                .unwrap()
                .with_no_client_auth()
                .with_single_cert(
                    vec![held.der.clone()],
                    PrivateKeyDer::Pkcs8(PrivatePkcs8KeyDer::from(held.key.clone())),
                )
                .unwrap();
        let acceptor = tokio_rustls::TlsAcceptor::from(Arc::new(config));
        let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
        let address = listener.local_addr().unwrap().to_string();
        let sent: Sent = Arc::new(Mutex::new(Vec::new()));
        let kept = sent.clone();
        tokio::spawn(async move {
            while let Ok((socket, _)) = listener.accept().await {
                let (acceptor, answer, kept) = (acceptor.clone(), answer.clone(), kept.clone());
                tokio::spawn(async move {
                    // A client that refused the certificate just hangs up.
                    let Ok(tls) = acceptor.accept(socket).await else { return };
                    let mut tls = BufReader::new(tls);
                    loop {
                        let mut line = String::new();
                        if tls.read_line(&mut line).await.unwrap_or(0) == 0 {
                            return;
                        }
                        let path = line.split(' ').nth(1).unwrap_or("").to_string();
                        let (mut authorization, mut length) = (None, 0);
                        loop {
                            let mut header = String::new();
                            tls.read_line(&mut header).await.unwrap();
                            let header = header.trim_end();
                            if header.is_empty() {
                                break;
                            }
                            let (name, value) = header.split_once(':').unwrap();
                            match name.to_lowercase().as_str() {
                                "authorization" => authorization = Some(value.trim().to_string()),
                                "content-length" => length = value.trim().parse().unwrap(),
                                _ => {}
                            }
                        }
                        let mut body = vec![0; length];
                        tls.read_exact(&mut body).await.unwrap();
                        kept.lock().unwrap().push((path.clone(), authorization.clone()));
                        let (status, body) = answer(&path, authorization.as_deref());
                        let head = format!("HTTP/1.1 {status} X\r\nContent-Length: {}\r\n\r\n", body.len());
                        let tls = tls.get_mut();
                        tls.write_all(head.as_bytes()).await.unwrap();
                        tls.write_all(&body).await.unwrap();
                        tls.flush().await.unwrap();
                    }
                });
            }
        });
        Self { address, sent }
    }

    fn sent(&self) -> Vec<(String, Option<String>)> {
        self.sent.lock().unwrap().clone()
    }
}

const VERSION: &str = r#"{"version":"1.12.0","contract":{"version":"1.60","major":1},"commit":"abc","build_date":"2026-10-29","license":"AGPL-3.0","product":"Toskar","source":"https://github.com/yeixio/toskar-core"}"#;

/// A computer away from home, and a relay that keeps its address record.
struct Away {
    held: Held,
    computer: Server,
    relay_held: Held,
    secret: String,
}

impl Away {
    async fn new() -> Self {
        let held = Held::new("Studio");
        let computer = Server::start(
            &held,
            Arc::new(|path, authorization| match path {
                "/api/v1/health" if authorization == Some("Bearer tk_away") => (200, br#"{"status":"ok"}"#.to_vec()),
                "/api/v1/health" => (401, br#"{"error":{"code":"UNAUTHORIZED","message":"no"}}"#.to_vec()),
                _ => (200, VERSION.as_bytes().to_vec()),
            }),
        )
        .await;
        Self {
            held,
            computer,
            relay_held: Held::new("localhost"),
            secret: URL_SAFE_NO_PAD.encode((0u8..32).collect::<Vec<_>>()),
        }
    }

    /// A record as Core writes it: signed by the computer's certificate, sealed with the route secret.
    fn record(&self, addresses: &[&str]) -> Vec<u8> {
        let route = records::route_id(&self.secret).unwrap();
        let payload = serde_json::to_vec(&json!({
            "v": 1, "route": route, "at": OffsetDateTime::now_utc().unix_timestamp(), "addresses": addresses,
        }))
        .unwrap();
        let rng = aws_lc_rs::rand::SystemRandom::new();
        let key = aws_lc_rs::signature::EcdsaKeyPair::from_pkcs8(
            &aws_lc_rs::signature::ECDSA_P256_SHA256_ASN1_SIGNING,
            &self.held.key,
        )
        .unwrap();
        let sig = key.sign(&rng, &payload).unwrap();
        let signed = serde_json::to_vec(&json!({
            "payload": STANDARD.encode(&payload),
            "cert": STANDARD.encode(&self.held.der),
            "alg": "ecdsa-sha256",
            "sig": STANDARD.encode(sig.as_ref()),
        }))
        .unwrap();
        let nonce: [u8; 12] = rand_bytes();
        let key = hkdf_sha256(&route_secret(&self.secret).unwrap(), "toskar route key", 32);
        let key = LessSafeKey::new(UnboundKey::new(&AES_256_GCM, &key).unwrap());
        let mut sealed = signed;
        key.seal_in_place_append_tag(
            Nonce::assume_unique_for_key(nonce),
            Aad::from(route.as_bytes()),
            &mut sealed,
        )
        .unwrap();
        [nonce.to_vec(), sealed].concat()
    }

    /// The relay, answering with body to anything.
    async fn relay(&self, status: u16, body: Vec<u8>) -> Server {
        Server::start(&self.relay_held, Arc::new(move |_, _| (status, body.clone()))).await
    }

    fn device(&self, home: &str, relay: &str, token: Option<&str>) -> Device {
        Device {
            address: home.into(),
            api_key: "tk_away".into(),
            pin: self.held.pin(),
            route: Some(Route {
                secret: self.secret.clone(),
                id: records::route_id(&self.secret).unwrap(),
                relay: relay.into(),
                token: token.map(Into::into),
            }),
        }
    }

    fn client(&self, device: Device) -> Client {
        // The relay's certificate is checked as any website's is; this one trusts the test relay's.
        let relay = reqwest::Client::builder()
            .tls_certs_only([reqwest::Certificate::from_der(&self.relay_held.der).unwrap()])
            .build()
            .unwrap();
        let mut builder = Client::builder()
            .device(device)
            .retries(0)
            .timeout(Duration::from_secs(5));
        builder.relay_http = Some(relay);
        builder.build().unwrap()
    }
}

fn rand_bytes<const N: usize>() -> [u8; N] {
    let mut out = [0; N];
    aws_lc_rs::rand::fill(&mut out).unwrap();
    out
}

/// An address that refuses connections: home, with the computer away.
fn nowhere() -> String {
    std::net::TcpListener::bind("127.0.0.1:0")
        .unwrap()
        .local_addr()
        .unwrap()
        .to_string()
}

/// The relay's address as a name, so its certificate for localhost matches.
fn named(server: &Server) -> String {
    server.address.replace("127.0.0.1", "localhost")
}

#[tokio::test]
async fn reaches_it_directly_from_its_record() {
    let away = Away::new().await;
    let relay = away.relay(200, away.record(&[&away.computer.address])).await;
    let toskar = away.client(away.device(&nowhere(), &named(&relay), Some("rt")));
    assert_eq!(toskar.path(), None);
    assert_eq!(toskar.version().await.unwrap().version, "1.12.0");
    assert_eq!(toskar.path(), Some(ConnectionPath::Direct));
    let asked = relay.sent();
    assert_eq!(
        asked[0],
        (
            format!("/v1/routes/{}/record", records::route_id(&away.secret).unwrap()),
            Some("Bearer rt".into())
        )
    );
}

#[tokio::test]
async fn takes_home_when_it_answers() {
    let away = Away::new().await;
    let relay = away.relay(404, Vec::new()).await;
    let toskar = away.client(away.device(&away.computer.address, &named(&relay), Some("rt")));
    toskar.version().await.unwrap();
    assert_eq!(toskar.path(), Some(ConnectionPath::Home));
    assert_eq!(toskar.reconnect().await.unwrap(), Some(ConnectionPath::Home));
    assert!(relay.sent().is_empty());
}

#[tokio::test]
async fn another_certificate_at_home_is_refused() {
    let away = Away::new().await;
    let mut device = away.device(&away.computer.address, "relay.test", Some("rt"));
    device.pin = format!("sha256:{}", "ab".repeat(32));
    assert_eq!(away.client(device).version().await.unwrap_err().code, "PIN_MISMATCH");
}

#[tokio::test]
async fn a_record_from_another_computer_is_refused() {
    let away = Away::new().await;
    let relay = away.relay(200, away.record(&[&away.computer.address])).await;
    let mut device = away.device(&nowhere(), &named(&relay), Some("rt"));
    device.pin = Held::new("Stranger").pin();
    assert_eq!(away.client(device).version().await.unwrap_err().code, "RECORD_PIN");
}

#[tokio::test]
async fn with_no_record_it_says_so() {
    let away = Away::new().await;
    let relay = away.relay(404, Vec::new()).await;
    let device = away.device(&nowhere(), &named(&relay), Some("rt"));
    assert_eq!(away.client(device).version().await.unwrap_err().code, "NO_RECORD");
}

#[tokio::test]
async fn toskars_relay_isnt_asked_without_a_token() {
    let away = Away::new().await;
    let device = away.device(&nowhere(), "relay.toskar.ai", None);
    assert_eq!(away.client(device).version().await.unwrap_err().code, "UNREACHABLE");
}

#[tokio::test]
async fn pairs_and_pins_what_it_saw() {
    let held = Held::new("Studio");
    let pin = held.pin();
    let paired = format!(
        r#"{{"api_key":"tk_new","key":{{"id":"k1","name":"Phone","prefix":"tk_n","created_at":"2026-10-30T00:00:00Z","revoked":false,"person_id":"p1","permissions":{{"memory":"read","knowledge":"read","tools":"none","placement":false}}}},"tls_fingerprint":"{pin}","tls_short":"{}"}}"#,
        records::short_pin(&pin)
    );
    let computer = Server::start(
        &held,
        Arc::new(move |path, _| match path {
            "/api/v1/devices/pair" => (200, paired.as_bytes().to_vec()),
            _ => (200, br#"{"status":"ok"}"#.to_vec()),
        }),
    )
    .await;
    let mut shown = String::new();
    let device = pair(&computer.address, "123456", "Test", |s| {
        shown = s.into();
        true
    })
    .await
    .unwrap();
    assert_eq!(
        device,
        Device {
            address: computer.address.clone(),
            api_key: "tk_new".into(),
            pin: pin.clone(),
            route: None
        }
    );
    assert_eq!(shown, records::short_pin(&pin));
    let declined = pair(&computer.address, "123456", "Test", |_| false).await;
    assert_eq!(declined.unwrap_err().code, "NOT_CONFIRMED");
}
