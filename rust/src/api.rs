use bytes::Bytes;
use serde::Serialize;

use crate::{Client, Error, Result};

/// Every route of Toskar Core's API, typed: `toskar.api().list_models()`
/// and so on, one async method for each operation, named after it. An
/// error answer is an [`Error`] with Toskar's code.
pub struct Api<'a> {
    pub(crate) client: &'a Client,
}

/// A request body as JSON.
pub(crate) fn json<T: Serialize>(body: &T) -> Result<(Bytes, &'static str)> {
    serde_json::to_vec(body)
        .map(|b| (Bytes::from(b), "application/json"))
        .map_err(|e| Error::new(0, "BAD_REQUEST", format!("The request didn't encode: {e}")).with_source(e))
}

/// A request body as it is, such as a file's bytes.
pub(crate) fn raw(body: impl Into<Bytes>, media: &'static str) -> (Bytes, &'static str) {
    (body.into(), media)
}
