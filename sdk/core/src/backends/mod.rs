//! Language backends that turn source into a WASM artifact.
//!
//! Each backend implements the [`CompileBackend`](crate::compile::CompileBackend)
//! trait. Today there's just one — Python via componentize-py — but the whole
//! point of the trait is that adding another language is only a matter of adding
//! another backend module here and wiring it up.

pub mod componentize_py;
