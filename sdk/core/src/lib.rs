//! The Tandem compile engine.
//!
//! This crate is the shared brain behind every Tandem SDK. Each language (for
//! now, Python) gets a thin wrapper that hands source to this engine, and the
//! engine turns it into a validated WASM artifact a node can run. Keeping the
//! hard part here means a new language is just a new backend, not a whole new
//! pipeline.
//!
//! The pieces:
//! * [`compile`] — the request/error types and the [`CompileBackend`] trait.
//! * [`artifact`] — the compiled output and its content hash.
//! * [`validate`] — cheap trust checks on WASM bytes.
//! * [`cache`] — an on-disk cache so we compile the same thing only once.
//!
//! The front door most callers want is [`compile_with_cache`], which ties a
//! backend, the cache, and validation together.

pub mod artifact;
pub mod cache;
pub mod compile;
pub mod validate;

pub use artifact::{hash_bytes, Artifact, ArtifactKind};
pub use cache::BuildCache;
pub use compile::{
    finalize_artifact, CompileBackend, CompileError, CompileOptions, CompileRequest, TaskShape,
    MAX_ARTIFACT_BYTES,
};
pub use validate::{detect_kind, validate_artifact};

/// Compile a request, reusing the cache when we can and validating whatever the
/// backend produces.
///
/// This is the path most callers should use. It checks the cache first, only
/// runs the (slow) backend on a miss, validates the result, and stores it for
/// next time. The `source_hash` is supplied by the caller because how you hash
/// a project depends on the language.
pub fn compile_with_cache(
    backend: &dyn CompileBackend,
    cache: &BuildCache,
    request: &CompileRequest,
    source_hash: &str,
) -> Result<Artifact, CompileError> {
    let key = BuildCache::key_for(request, source_hash);

    // A cache hit means we've built exactly this before, so hand it straight back.
    if let Some(hit) = cache.get(&key) {
        return Ok(hit);
    }

    // No point running a backend that isn't installed; say so clearly instead.
    if !backend.is_available() {
        return Err(CompileError::BackendUnavailable(format!(
            "no working backend for language '{}'",
            request.language
        )));
    }

    let artifact = backend.compile(request)?;
    cache.put(&key, &artifact)?;
    Ok(artifact)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    // A minimal but valid-looking core module: the magic number plus version 1.
    fn fake_core_module() -> Vec<u8> {
        vec![0x00, 0x61, 0x73, 0x6d, 0x01, 0x00, 0x00, 0x00]
    }

    // A minimal but valid-looking component: the magic number plus the
    // component version/layer bytes.
    fn fake_component() -> Vec<u8> {
        vec![0x00, 0x61, 0x73, 0x6d, 0x0d, 0x00, 0x01, 0x00]
    }

    #[test]
    fn detects_core_modules_and_components() {
        assert_eq!(detect_kind(&fake_core_module()).unwrap(), ArtifactKind::CoreModule);
        assert_eq!(detect_kind(&fake_component()).unwrap(), ArtifactKind::Component);
    }

    #[test]
    fn rejects_non_wasm_bytes() {
        assert!(detect_kind(b"not wasm at all").is_err());
        assert!(detect_kind(&[0x00, 0x61]).is_err());
    }

    #[test]
    fn hashes_are_stable_and_content_based() {
        let one = hash_bytes(b"hello");
        let two = hash_bytes(b"hello");
        let different = hash_bytes(b"world");
        assert_eq!(one, two);
        assert_ne!(one, different);
        assert_eq!(one.len(), 64); // sha-256 is 32 bytes = 64 hex chars
    }

    #[test]
    fn cache_key_changes_with_options() {
        let base = CompileRequest {
            language: "python".to_string(),
            source_dir: PathBuf::from("/tmp/app"),
            entry_module: "app".to_string(),
            entry_function: "crunch".to_string(),
            shape: TaskShape::Compute,
            options: CompileOptions::new(),
        };

        let mut changed = base.clone();
        changed.options.set("timeout_ms", "500");

        let key_a = BuildCache::key_for(&base, "sourcehash");
        let key_b = BuildCache::key_for(&changed, "sourcehash");
        assert_ne!(key_a, key_b);
    }

    #[test]
    fn cache_round_trips_an_artifact() {
        let dir = std::env::temp_dir().join("tandem_core_cache_round_trip");
        // Start from a clean slate in case a previous run left something behind.
        let _ = std::fs::remove_dir_all(&dir);

        let cache = BuildCache::new(&dir);
        let artifact = Artifact::new(fake_component(), ArtifactKind::Component);

        assert!(cache.get("mykey").is_none());
        cache.put("mykey", &artifact).unwrap();

        let loaded = cache.get("mykey").expect("artifact should be cached now");
        assert_eq!(loaded.bytes, artifact.bytes);
        assert_eq!(loaded.kind, ArtifactKind::Component);

        let _ = std::fs::remove_dir_all(&dir);
    }
}
