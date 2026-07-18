//! A small on-disk cache so we only compile the same thing once.
//!
//! Compiling with a real toolchain (like componentize-py) is slow, so the
//! engine keys finished artifacts by a content hash of the request and reuses
//! them. The cache is deliberately dumb: files named by their key, nothing
//! fancy, and you can clear it by deleting the directory.

use std::fs;
use std::path::PathBuf;

use crate::artifact::{hash_bytes, Artifact};
use crate::compile::{CompileError, CompileRequest, MAX_ARTIFACT_BYTES};
use crate::validate::validate_artifact;

/// Reads and writes compiled artifacts under a directory on disk.
pub struct BuildCache {
    root: PathBuf,
}

impl BuildCache {
    /// Point the cache at a directory. The directory is created lazily the
    /// first time we actually store something.
    pub fn new(root: impl Into<PathBuf>) -> Self {
        Self { root: root.into() }
    }

    /// Build a stable cache key from the request plus a hash of its source.
    ///
    /// The source hash is passed in because how you hash a project (one file,
    /// a whole directory) depends on the language backend. Everything that can
    /// change the output is folded into the key so a stale entry never gets
    /// reused by mistake.
    pub fn key_for(request: &CompileRequest, source_hash: &str) -> String {
        let mut material = String::new();
        material.push_str(&request.language);
        material.push('\n');
        material.push_str(&request.entry_module);
        material.push('\n');
        material.push_str(&request.entry_function);
        material.push('\n');
        material.push_str(request.shape.as_str());
        material.push('\n');
        for (key, value) in &request.options.values {
            material.push_str(key);
            material.push('=');
            material.push_str(value);
            material.push('\n');
        }
        material.push_str(source_hash);
        hash_bytes(material.as_bytes())
    }

    /// Where on disk a given key lives.
    fn path_for(&self, key: &str) -> PathBuf {
        self.root.join(format!("{key}.wasm"))
    }

    /// Look for a cached artifact. Returns `None` on a miss.
    ///
    /// A missing or corrupt cache file is treated as a miss rather than an
    /// error, so a bad entry can never wedge a build. We also re-validate the
    /// bytes on the way out so we never trust a tampered cache file.
    pub fn get(&self, key: &str) -> Option<Artifact> {
        let path = self.path_for(key);
        let bytes = fs::read(&path).ok()?;
        let kind = validate_artifact(&bytes, MAX_ARTIFACT_BYTES).ok()?;
        Some(Artifact::new(bytes, kind))
    }

    /// Store an artifact under a key, creating the cache directory if needed.
    pub fn put(&self, key: &str, artifact: &Artifact) -> Result<(), CompileError> {
        fs::create_dir_all(&self.root).map_err(|error| CompileError::Io(error.to_string()))?;
        let path = self.path_for(key);
        fs::write(&path, &artifact.bytes).map_err(|error| CompileError::Io(error.to_string()))?;
        Ok(())
    }
}
