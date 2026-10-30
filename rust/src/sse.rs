//! Server-sent events, read from a response as they come.

use bytes::{Buf, BytesMut};
use futures_util::{Stream, StreamExt, stream};

use crate::{Error, Result};

/// One server-sent event.
pub(crate) struct Event {
    pub name: String,
    pub data: String,
}

/// The events of a response's body, in order. A body that breaks off is
/// `CONNECTION_LOST`; one that ends ends the stream.
pub(crate) fn events(response: reqwest::Response) -> impl Stream<Item = Result<Event>> + Send {
    struct State<S> {
        body: S,
        buffer: BytesMut,
        done: bool,
    }
    let state = State {
        body: Box::pin(response.bytes_stream()),
        buffer: BytesMut::new(),
        done: false,
    };
    stream::unfold(state, |mut s| async move {
        let mut name = String::from("message");
        let mut data = String::new();
        let mut any = false;
        loop {
            // A whole line, or more of the body.
            if let Some(end) = s.buffer.iter().position(|&b| b == b'\n') {
                let mut line = s.buffer.split_to(end + 1);
                line.truncate(end);
                if line.last() == Some(&b'\r') {
                    line.truncate(end - 1);
                }
                let line = String::from_utf8_lossy(&line).into_owned();
                if line.is_empty() {
                    if any {
                        return Some((Ok(Event { name, data }), s));
                    }
                    continue;
                }
                if line.starts_with(':') {
                    continue;
                }
                let (field, value) = match line.split_once(':') {
                    Some((f, v)) => (f.to_string(), v.strip_prefix(' ').unwrap_or(v).to_string()),
                    None => (line.clone(), String::new()),
                };
                match field.as_str() {
                    "event" => {
                        name = value;
                        any = true;
                    }
                    "data" => {
                        if !data.is_empty() {
                            data.push('\n');
                        }
                        data.push_str(&value);
                        any = true;
                    }
                    _ => {}
                }
                continue;
            }
            if s.done {
                if any {
                    return Some((Ok(Event { name, data }), s));
                }
                return None;
            }
            match s.body.next().await {
                Some(Ok(chunk)) => s.buffer.extend_from_slice(chunk.chunk()),
                Some(Err(e)) => {
                    s.done = true;
                    s.buffer.clear();
                    let lost =
                        Error::new(200, "CONNECTION_LOST", "The answer stopped before it finished").with_source(e);
                    return Some((Err(lost), s));
                }
                None => s.done = true,
            }
        }
    })
}
