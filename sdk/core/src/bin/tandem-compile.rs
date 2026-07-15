//! `tandem-compile` — the command-line front door to the Tandem compile engine.
//!
//! The CLI shells out to this binary to turn a user's marked function into a
//! WASM component. It wires up the right language backend, runs the shared
//! compile-with-cache path, and writes the resulting artifact to disk. Keeping
//! this a thin binary means the CLI (and any other tool) can compile a task
//! without embedding the engine.

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

use tandem_core::backends::componentize_py::ComponentizePyBackend;
use tandem_core::{
    compile_with_cache, hash_bytes, BuildCache, CompileBackend, CompileOptions, CompileRequest,
    TaskShape,
};

fn main() {
    match run() {
        Ok(message) => println!("{message}"),
        Err(message) => {
            eprintln!("tandem-compile: {message}");
            std::process::exit(1);
        }
    }
}

fn run() -> Result<String, String> {
    let parsed = parse_args()?;

    // Pick the backend for this language. Python is the only one today, but this
    // match is the single place a new language plugs in.
    let backend: Box<dyn CompileBackend> = match parsed.language.as_str() {
        "python" => Box::new(ComponentizePyBackend::new(
            vec![parsed.componentize_py.clone()],
            &parsed.wit_dir,
        )),
        other => return Err(format!("no compile backend for language '{other}'")),
    };

    let request = CompileRequest {
        language: parsed.language.clone(),
        source_dir: parsed.source.clone(),
        entry_module: parsed.entry_module.clone(),
        entry_function: parsed.entry_function.clone(),
        shape: parsed.shape,
        options: parsed.options.clone(),
    };

    let source_hash = hash_source_dir(&parsed.source).map_err(|error| error.to_string())?;
    let cache = BuildCache::new(&parsed.cache_dir);

    let artifact = compile_with_cache(backend.as_ref(), &cache, &request, &source_hash)
        .map_err(|error| error.to_string())?;

    std::fs::write(&parsed.out, &artifact.bytes).map_err(|error| error.to_string())?;

    Ok(format!(
        "compiled {} ({}, {} bytes) -> {}",
        artifact.content_hash,
        artifact.kind.as_str(),
        artifact.len(),
        parsed.out.display()
    ))
}

/// The command-line inputs, once parsed and defaulted.
struct Args {
    source: PathBuf,
    entry_module: String,
    entry_function: String,
    language: String,
    wit_dir: PathBuf,
    componentize_py: String,
    cache_dir: PathBuf,
    out: PathBuf,
    shape: TaskShape,
    options: CompileOptions,
}

/// Parse the command line. Every flag we understand takes exactly one value, and
/// `--option key=value` may be repeated.
fn parse_args() -> Result<Args, String> {
    let raw: Vec<String> = std::env::args().skip(1).collect();
    let mut single: BTreeMap<String, String> = BTreeMap::new();
    let mut option_pairs: Vec<String> = Vec::new();

    let mut index = 0;
    while index < raw.len() {
        let flag = &raw[index];
        let value = raw
            .get(index + 1)
            .ok_or_else(|| format!("missing value for {flag}"))?;
        match flag.as_str() {
            "--option" => option_pairs.push(value.clone()),
            "--source" | "--entry-module" | "--entry-function" | "--language" | "--wit-dir"
            | "--componentize-py" | "--cache" | "--out" | "--shape" => {
                single.insert(flag.trim_start_matches("--").to_string(), value.clone());
            }
            other => return Err(format!("unknown flag: {other}")),
        }
        index += 2;
    }

    let require = |key: &str| {
        single
            .get(key)
            .cloned()
            .ok_or_else(|| format!("--{key} is required"))
    };

    let shape = match single.get("shape").map(String::as_str) {
        Some("serve") => TaskShape::Serve,
        _ => TaskShape::Compute,
    };

    let mut options = CompileOptions::new();
    for pair in &option_pairs {
        let (key, value) = pair
            .split_once('=')
            .ok_or_else(|| format!("--option must be key=value, got '{pair}'"))?;
        options.set(key, value);
    }

    Ok(Args {
        source: PathBuf::from(require("source")?),
        entry_module: require("entry-module")?,
        entry_function: require("entry-function")?,
        language: single
            .get("language")
            .cloned()
            .unwrap_or_else(|| "python".to_string()),
        wit_dir: PathBuf::from(require("wit-dir")?),
        componentize_py: single
            .get("componentize-py")
            .cloned()
            .unwrap_or_else(|| "componentize-py".to_string()),
        cache_dir: PathBuf::from(require("cache")?),
        out: PathBuf::from(require("out")?),
        shape,
        options,
    })
}

/// Hash all the Python source under `dir` so the build cache knows when anything
/// the compile depends on has changed. Both file paths and contents go into the
/// hash, so a rename or an edit both bust the cache.
fn hash_source_dir(dir: &Path) -> std::io::Result<String> {
    let mut files: Vec<PathBuf> = Vec::new();
    collect_python_files(dir, &mut files)?;
    files.sort();

    let mut material: Vec<u8> = Vec::new();
    for file in &files {
        if let Ok(relative) = file.strip_prefix(dir) {
            material.extend_from_slice(relative.to_string_lossy().as_bytes());
        }
        material.push(0);
        let contents = std::fs::read(file)?;
        material.extend_from_slice(&contents);
        material.push(0);
    }
    Ok(hash_bytes(&material))
}

/// Walk `dir` collecting every `.py` file, skipping noise like caches and VCS dirs.
fn collect_python_files(dir: &Path, out: &mut Vec<PathBuf>) -> std::io::Result<()> {
    for entry in std::fs::read_dir(dir)? {
        let entry = entry?;
        let path = entry.path();
        if path.is_dir() {
            let name = path.file_name().and_then(|n| n.to_str()).unwrap_or("");
            if name == "__pycache__" || name == ".git" || name.ends_with(".egg-info") {
                continue;
            }
            collect_python_files(&path, out)?;
        } else if path.extension().and_then(|e| e.to_str()) == Some("py") {
            out.push(path);
        }
    }
    Ok(())
}
