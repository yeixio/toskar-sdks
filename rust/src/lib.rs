//! The official Rust SDK for [Toskar](https://toskar.ai): local AI across
//! your own computers.
//!
//! ```no_run
//! use futures_util::StreamExt;
//! use toskar::{ChatEvent, Client, models::ChatRequest};
//!
//! # async fn run() -> toskar::Result<()> {
//! let toskar = Client::new()?;
//! let request = ChatRequest { message: "Plan a three-day trip to Juneau".into(), ..Default::default() };
//! let mut events = toskar.chat_stream(&request).await?;
//! while let Some(event) = events.next().await {
//!     if let ChatEvent::Token(text) = event? {
//!         print!("{text}");
//!     }
//! }
//! # Ok(())
//! # }
//! ```
//!
//! [`Client::api`] reaches every route, typed from Toskar Core's API spec:
//! `toskar.api().list_models().await?`.

mod api;
mod client;
mod error;
mod generated;
mod sse;

pub use api::Api;
pub use client::{Builder, ChatEvent, Client, DEFAULT_URL};
pub use error::{Error, Result};
pub use generated::codes::{CONTRACT_VERSION, error_codes};
pub use generated::models;
