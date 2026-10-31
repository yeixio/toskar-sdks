//! Finding computers running Toskar Core on the home network, as the Toskar
//! apps do: they advertise _localai._tcp over mDNS, with where their API is
//! in the TXT record (Toskar Core's docs/connecting.md).
//!
//! It asks with one mDNS query and reads the answers itself (RFC 6762): one
//! service type needs a few dozen lines, not a library.

use std::collections::{HashMap, HashSet};
use std::net::{IpAddr, Ipv4Addr, SocketAddr, SocketAddrV4};
use std::time::{Duration, Instant};

use futures_util::future::join_all;
use socket2::{Domain, Protocol, Socket, Type};

use crate::{Error, Result};

/// What Toskar Core advertises over mDNS.
pub const SERVICE_TYPE: &str = "_localai._tcp";

const GROUP: Ipv4Addr = Ipv4Addr::new(224, 0, 0, 251);
const PORT: u16 = 5353;

/// A Toskar Core found on the network.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct DiscoveredComputer {
    /// The computer's name.
    pub name: String,
    /// The computer's node ID.
    pub node_id: String,
    /// Toskar Core's version.
    pub version: String,
    /// The API's host:port, to pair with: the first of `addresses` that answers.
    pub address: String,
    /// Every host:port found for the computer. A computer can have addresses
    /// this device can't reach, such as a container network's.
    pub addresses: Vec<String>,
    /// False when the API answers only on that computer: say to turn on
    /// Connect a device there, rather than that it's unreachable.
    pub on_network: bool,
}

/// Asks the network for timeout and answers the computers that answered, by name.
///
/// ```no_run
/// # async fn run() -> toskar::Result<()> {
/// for computer in toskar::find(std::time::Duration::from_secs(3)).await? {
///     println!("{} {}", computer.name, computer.address);
/// }
/// # Ok(())
/// # }
/// ```
pub async fn find(timeout: Duration) -> Result<Vec<DiscoveredComputer>> {
    let found = browse(timeout).await.map_err(|e| {
        Error::new(
            0,
            "DISCOVERY_FAILED",
            format!("Couldn't look for computers on the network: {e}"),
        )
        .with_source(e)
    })?;
    let computers = join_all(found.iter().map(|s| computer(&s.txt, &s.instance, &s.hosts, reachable))).await;
    let mut seen = HashSet::new();
    let mut out: Vec<_> = computers
        .into_iter()
        .flatten()
        .filter(|c| seen.insert(format!("{}{}", c.node_id, c.address)))
        .collect();
    out.sort_by(|a, b| a.name.cmp(&b.name));
    Ok(out)
}

/// A service that answered: its instance name, TXT record, and its host's addresses.
pub(crate) struct Service {
    pub(crate) instance: String,
    pub(crate) txt: HashMap<String, String>,
    pub(crate) hosts: Vec<IpAddr>,
}

/// Asks on every interface that can reach a home network, at once and again
/// a second later, and reads the answers for timeout. A computer with a
/// container network or a VPN has more than one interface, and the home
/// network's may not be first.
async fn browse(timeout: Duration) -> std::io::Result<Vec<Service>> {
    let interfaces: Vec<Ipv4Addr> = if_addrs::get_if_addrs()?
        .into_iter()
        .filter(|i| !i.is_loopback())
        .filter_map(|i| match i.ip() {
            IpAddr::V4(a) if !a.is_link_local() => Some(a),
            _ => None,
        })
        .collect();
    let socket = Socket::new(Domain::IPV4, Type::DGRAM, Some(Protocol::UDP))?;
    // The computer's own mDNS responder has the port too.
    socket.set_reuse_address(true)?;
    #[cfg(unix)]
    socket.set_reuse_port(true)?;
    socket.bind(&SocketAddr::from((Ipv4Addr::UNSPECIFIED, PORT)).into())?;
    for local in &interfaces {
        let _ = socket.join_multicast_v4(&GROUP, local);
    }
    socket.set_nonblocking(true)?;
    let socket = tokio::net::UdpSocket::from_std(socket.into())?;
    let query = query(&format!("{SERVICE_TYPE}.local"));
    let ask = || {
        for local in &interfaces {
            let sent = socket2::SockRef::from(&socket).set_multicast_if_v4(local);
            if sent.is_ok() {
                let _ = socket.try_send_to(&query, SocketAddrV4::new(GROUP, PORT).into());
            }
        }
    };
    ask();
    let mut asked_again = false;
    let mut records = Answers::default();
    let started = Instant::now();
    let mut buffer = vec![0; 9000];
    loop {
        let elapsed = started.elapsed();
        if elapsed >= timeout {
            break;
        }
        if !asked_again && elapsed >= Duration::from_secs(1) {
            ask();
            asked_again = true;
        }
        let wait = (timeout - elapsed).min(Duration::from_millis(250));
        if let Ok(Ok((n, _))) = tokio::time::timeout(wait, socket.recv_from(&mut buffer)).await {
            // Anything that isn't a well-formed answer is someone else's to worry about.
            let _ = records.read(&buffer[..n]);
        }
    }
    Ok(records.services(&format!("{SERVICE_TYPE}.local")))
}

const TYPE_A: usize = 1;
const TYPE_PTR: usize = 12;
const TYPE_TXT: usize = 16;
const TYPE_AAAA: usize = 28;
const TYPE_SRV: usize = 33;

/// A query for name's PTR records, as a one-shot querier sends it.
pub(crate) fn query(name: &str) -> Vec<u8> {
    let mut message = vec![0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0];
    for label in name.split('.') {
        message.push(label.len() as u8);
        message.extend_from_slice(label.as_bytes());
    }
    message.extend_from_slice(&[0, 0, TYPE_PTR as u8, 0, 1]);
    message
}

/// A message that doesn't read as one.
#[derive(Debug)]
pub(crate) struct Malformed;

/// The records the answers held, by name, gathered across packets.
#[derive(Default)]
pub(crate) struct Answers {
    ptr: HashMap<String, Vec<String>>,
    srv: HashMap<String, String>,
    txt: HashMap<String, HashMap<String, String>>,
    hosts: HashMap<String, Vec<IpAddr>>,
}

impl Answers {
    /// Reads one mDNS message's records: answers and additional ones alike.
    pub(crate) fn read(&mut self, m: &[u8]) -> std::result::Result<(), Malformed> {
        let mut r = Reader { m, at: 0 };
        if r.u16(2)? & 0x8000 == 0 {
            return Ok(()); // a query, not an answer
        }
        let questions = r.u16(4)?;
        let count = r.u16(6)? + r.u16(8)? + r.u16(10)?;
        r.at = 12;
        for _ in 0..questions {
            r.name()?;
            r.at += 4;
        }
        for _ in 0..count {
            let name = r.name()?.to_lowercase();
            let kind = r.u16(r.at)?;
            let length = r.u16(r.at + 8)?;
            let data = r.at + 10;
            r.at = data + length;
            let body = m.get(data..r.at).ok_or(Malformed)?;
            match kind {
                TYPE_PTR => {
                    let target = Reader { m, at: data }.name()?;
                    let list = self.ptr.entry(name).or_default();
                    if !list.contains(&target) {
                        list.push(target);
                    }
                }
                TYPE_SRV => {
                    let target = Reader { m, at: data + 6 }.name()?.to_lowercase();
                    self.srv.insert(name, target);
                }
                TYPE_TXT => {
                    self.txt.insert(name, text(body));
                }
                TYPE_A | TYPE_AAAA => {
                    let ip = match body.len() {
                        4 => IpAddr::from(<[u8; 4]>::try_from(body).map_err(|_| Malformed)?),
                        16 => IpAddr::from(<[u8; 16]>::try_from(body).map_err(|_| Malformed)?),
                        _ => continue,
                    };
                    let list = self.hosts.entry(name).or_default();
                    if !list.contains(&ip) {
                        list.push(ip);
                    }
                }
                _ => {}
            }
        }
        Ok(())
    }

    /// The instances of a service type, with what their records say.
    pub(crate) fn services(&self, kind: &str) -> Vec<Service> {
        let suffix = format!(".{}", kind.to_lowercase());
        self.ptr
            .get(&kind.to_lowercase())
            .into_iter()
            .flatten()
            .filter_map(|full| {
                let key = full.to_lowercase();
                let target = self.srv.get(&key)?;
                let instance = if key.ends_with(&suffix) {
                    full[..full.len() - suffix.len()].to_string()
                } else {
                    full.clone()
                };
                Some(Service {
                    instance,
                    txt: self.txt.get(&key).cloned().unwrap_or_default(),
                    hosts: self.hosts.get(target).cloned().unwrap_or_default(),
                })
            })
            .collect()
    }
}

fn text(body: &[u8]) -> HashMap<String, String> {
    let mut entries = HashMap::new();
    let mut i = 0;
    while i < body.len() {
        let n = usize::from(body[i]);
        let Some(entry) = body.get(i + 1..i + 1 + n) else { break };
        let entry = String::from_utf8_lossy(entry);
        if !entry.is_empty() {
            let (key, value) = entry.split_once('=').unwrap_or((&entry, ""));
            entries.insert(key.to_lowercase(), value.to_string());
        }
        i += 1 + n;
    }
    entries
}

/// Reads DNS names, with their compression, and numbers from a message.
struct Reader<'a> {
    m: &'a [u8],
    at: usize,
}

impl Reader<'_> {
    fn u16(&self, i: usize) -> std::result::Result<usize, Malformed> {
        let b = self.m.get(i..i + 2).ok_or(Malformed)?;
        Ok((usize::from(b[0]) << 8) | usize::from(b[1]))
    }

    fn name(&mut self) -> std::result::Result<String, Malformed> {
        let mut labels = Vec::new();
        let mut i = self.at;
        let mut jumped = false;
        let mut jumps = 0;
        loop {
            let n = usize::from(*self.m.get(i).ok_or(Malformed)?);
            if n == 0 {
                if !jumped {
                    self.at = i + 1;
                }
                return Ok(labels.join("."));
            }
            if n & 0xc0 == 0xc0 {
                if !jumped {
                    self.at = i + 2;
                }
                jumped = true;
                jumps += 1;
                if jumps > 32 {
                    return Err(Malformed); // a name that points in circles
                }
                i = ((n & 0x3f) << 8) | usize::from(*self.m.get(i + 1).ok_or(Malformed)?);
            } else {
                let label = self.m.get(i + 1..i + 1 + n).ok_or(Malformed)?;
                labels.push(String::from_utf8_lossy(label).into_owned());
                i += 1 + n;
            }
        }
    }
}

/// The computer a service describes, with the API's port from its TXT
/// record (the service's own port is for computers pairing with each
/// other), or `None` without one or without an address.
pub(crate) async fn computer<F, R>(
    txt: &HashMap<String, String>,
    instance: &str,
    hosts: &[IpAddr],
    reachable: F,
) -> Option<DiscoveredComputer>
where
    F: FnOnce(Vec<String>) -> R,
    R: Future<Output = Option<String>>,
{
    let port: u16 = txt.get("api_port")?.parse().ok().filter(|p| *p > 0)?;
    let mut ordered: Vec<&IpAddr> = hosts
        .iter()
        // A link-local IPv6 address needs its interface, which a URL can't carry.
        .filter(|a| !matches!(a, IpAddr::V6(v6) if v6.is_unicast_link_local()))
        .collect();
    ordered.sort_by_key(|a| a.is_ipv6());
    let mut addresses: Vec<String> = Vec::new();
    for a in ordered {
        // Rust writes IPv6 in its short form (RFC 5952), as the other SDKs do.
        let address = SocketAddr::new(*a, port).to_string();
        if !addresses.contains(&address) {
            addresses.push(address);
        }
    }
    let first = addresses.first()?.clone();
    let name = txt.get("name").filter(|n| !n.is_empty()).cloned();
    let answered = reachable(addresses.clone()).await;
    Some(DiscoveredComputer {
        name: name.unwrap_or_else(|| instance.to_string()),
        node_id: txt.get("node_id").cloned().unwrap_or_default(),
        version: txt.get("version").cloned().unwrap_or_default(),
        address: answered.unwrap_or(first),
        addresses,
        on_network: txt.get("api_lan").map(String::as_str) != Some("false"),
    })
}

/// The first of addresses that takes a TCP connection, tried together.
async fn reachable(addresses: Vec<String>) -> Option<String> {
    let tries = addresses.iter().map(|address| async move {
        let connected = tokio::time::timeout(
            Duration::from_millis(700),
            tokio::net::TcpStream::connect(address.as_str()),
        )
        .await;
        matches!(connected, Ok(Ok(_)))
    });
    let answered = join_all(tries).await;
    addresses.into_iter().zip(answered).find(|(_, ok)| *ok).map(|(a, _)| a)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn txt() -> HashMap<String, String> {
        [
            ("api_port", "7331"),
            ("name", "Studio"),
            ("node_id", "n1"),
            ("version", "1.12.0"),
        ]
        .into_iter()
        .map(|(k, v)| (k.into(), v.into()))
        .collect()
    }

    fn v4() -> IpAddr {
        "192.168.1.20".parse().unwrap()
    }

    fn v6() -> IpAddr {
        "fd00::20".parse().unwrap()
    }

    fn link_local() -> IpAddr {
        "fe80::1".parse().unwrap()
    }

    async fn none(_: Vec<String>) -> Option<String> {
        None
    }

    #[tokio::test]
    async fn a_service_is_a_computer_at_its_api_port() {
        let c = computer(&txt(), "studio-instance", &[v6(), link_local(), v4()], none)
            .await
            .unwrap();
        assert_eq!(c.name, "Studio");
        assert_eq!(c.node_id, "n1");
        assert_eq!(c.version, "1.12.0");
        // IPv4 first, IPv6 in brackets, and no link-local address.
        assert_eq!(c.addresses, ["192.168.1.20:7331", "[fd00::20]:7331"]);
        assert_eq!(c.address, "192.168.1.20:7331");
        assert!(c.on_network);
    }

    #[tokio::test]
    async fn the_address_is_the_one_that_answers() {
        let c = computer(
            &txt(),
            "x",
            &[v4(), v6()],
            |a: Vec<String>| async move { a.last().cloned() },
        )
        .await
        .unwrap();
        assert_eq!(c.address, "[fd00::20]:7331");
    }

    #[tokio::test]
    async fn without_a_name_its_the_instance_and_it_can_be_only_on_its_computer() {
        let mut txt = txt();
        txt.remove("name");
        txt.insert("api_lan".into(), "false".into());
        let c = computer(&txt, "studio-instance", &[v4()], none).await.unwrap();
        assert_eq!(c.name, "studio-instance");
        assert!(!c.on_network);
    }

    #[tokio::test]
    async fn without_an_api_port_or_address_it_isnt_one() {
        let mut no_port = txt();
        no_port.remove("api_port");
        assert_eq!(computer(&no_port, "x", &[v4()], none).await, None);
        assert_eq!(computer(&txt(), "x", &[link_local()], none).await, None);
    }

    /// An mDNS answer as a responder sends one: PTR, then SRV, TXT, and A in
    /// the additional records, names compressed.
    fn answer() -> Vec<u8> {
        let mut m = Vec::new();
        fn u16(m: &mut Vec<u8>, v: usize) {
            m.extend_from_slice(&[(v >> 8) as u8, (v & 0xff) as u8]);
        }
        fn labels(m: &mut Vec<u8>, labels: &[&str]) {
            for l in labels {
                m.push(l.len() as u8);
                m.extend_from_slice(l.as_bytes());
            }
        }
        for v in [0, 0x8400, 0, 1, 0, 3] {
            u16(&mut m, v);
        }
        // _localai._tcp.local PTR Studio._localai._tcp.local
        let type_at = m.len();
        labels(&mut m, &["_localai", "_tcp", "local"]);
        m.push(0);
        for v in [12, 1, 0, 120, 9] {
            u16(&mut m, v);
        }
        labels(&mut m, &["Studio"]);
        u16(&mut m, 0xc000 | type_at);
        let instance_at = m.len() - 9;
        // Studio._localai._tcp.local SRV 0 0 7332 studio.local
        for v in [0xc000 | instance_at, 33, 0x8001, 0, 120, 6 + 7 + 2, 0, 0, 7332] {
            u16(&mut m, v);
        }
        let host_at = m.len();
        labels(&mut m, &["studio"]);
        u16(&mut m, 0xc000 | (type_at + 14));
        // TXT
        let txt = ["api_port=7331", "node_id=n1", "name=Studio", "version=1.12.0"];
        let length = txt.iter().map(|t| t.len() + 1).sum();
        for v in [0xc000 | instance_at, 16, 0x8001, 0, 120, length] {
            u16(&mut m, v);
        }
        labels(&mut m, &txt);
        // studio.local A 192.168.1.20
        for v in [0xc000 | host_at, 1, 0x8001, 0, 120, 4] {
            u16(&mut m, v);
        }
        m.extend_from_slice(&[192, 168, 1, 20]);
        m
    }

    #[tokio::test]
    async fn reads_an_answer_with_compressed_names() {
        let mut answers = Answers::default();
        answers.read(&answer()).unwrap();
        // A query on the network isn't an answer.
        answers.read(&query("_localai._tcp.local")).unwrap();
        // Nor is a message cut short.
        assert!(answers.read(&answer()[..40]).is_err());
        let services = answers.services("_localai._tcp.local");
        assert_eq!(services.len(), 1);
        let s = &services[0];
        assert_eq!(s.instance, "Studio");
        assert_eq!(s.txt["api_port"], "7331");
        assert_eq!(s.hosts, [v4()]);
        let c = computer(&s.txt, &s.instance, &s.hosts, none).await.unwrap();
        assert_eq!(c.address, "192.168.1.20:7331");
    }
}
