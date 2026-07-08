from __future__ import annotations

import os

import tandem
from tandem import Immutable, TandemBuildError, TandemValidationError, compute, split
from tandem.builder import build_project


# These globals are wrapped in Immutable so Tandem's independence validator
# allows task functions to read them safely.
DEFAULT_BIAS = Immutable(0.10)

# Using the typed Immutable[...] form
SCORE_THRESHOLDS = Immutable[tuple[float, float]]((0.25, 0.75))

# Using Immutable.of(...)
LABEL_BY_BUCKET = Immutable.of({
    0: "low",
    1: "medium",
    2: "high",
})

# Using Immutable.of_type(...)
TOKEN_WEIGHTS = Immutable.of_type(
    dict[str, float],
    {
        "fast": 0.40,
        "secure": 0.35,
        "reliable": 0.30,
        "distributed": 0.45,
        "python": 0.15,
        "sdk": 0.10,
        "simple": 0.05,
        "smart": 0.12,
    },
)


@compute(batch=16, timeout_ms=40)
def tokenize(text: str) -> list[str]:
    """
    Small per-item task.
    Good fit for @compute because each call is independent and cheap.
    """
    cleaned = text.lower()
    cleaned = cleaned.replace(",", " ")
    cleaned = cleaned.replace(".", " ")
    cleaned = cleaned.replace("!", " ")
    cleaned = cleaned.replace("?", " ")

    raw_parts = cleaned.split()
    tokens: list[str] = []

    for part in raw_parts:
        if len(part) > 1:
            tokens.append(part)

    return tokens


@compute(batch=16, timeout_ms=75)
def extract_weighted_features(tokens: list[str]) -> dict[str, float]:
    """
    Another independent task that reads immutable global config.
    """
    features: dict[str, float] = {}

    for token in tokens:
        if token in TOKEN_WEIGHTS:
            features[token] = TOKEN_WEIGHTS[token]

    return features


def score_feature_map(features: dict[str, float]) -> float:
    """
    Single-item pure function.

    This is a nice candidate for tandem.split(...), because we usually
    want to run the same scoring logic across many documents at once.
    """
    score = DEFAULT_BIAS.value

    for key in features:
        score += features[key]

    return score


# split() turns a single-item function into a batched data-parallel function.
# It preserves input order in the returned list.
score_many_feature_maps = split(score_feature_map, chunk=64)


@compute(batch=32, timeout_ms=30)
def label_score(score: float) -> str:
    """
    Lightweight post-processing task.
    """
    low_cutoff = SCORE_THRESHOLDS.value[0]
    high_cutoff = SCORE_THRESHOLDS.value[1]

    if score < low_cutoff:
        return LABEL_BY_BUCKET[0]
    if score < high_cutoff:
        return LABEL_BY_BUCKET[1]
    return LABEL_BY_BUCKET[2]


@compute(batch=1, timeout_ms=250)
def summarize_scores(scores: list[float]) -> dict[str, float]:
    """
    Final aggregation step.

    The return type stays WASM-friendly by using dict[str, float].
    """
    total = 0.0
    count = 0
    min_score = 0.0
    max_score = 0.0

    for score in scores:
        total += score

        if count == 0:
            min_score = score
            max_score = score
        else:
            if score < min_score:
                min_score = score
            if score > max_score:
                max_score = score

        count += 1

    average = total / count if count else 0.0

    return {
        "count": float(count),
        "min": min_score,
        "avg": average,
        "max": max_score,
    }


def local_smoke_test() -> None:
    """
    This runs everything locally without contacting a Tandem server.

    The SDK checks TANDEM_WORKER=1 and executes task bodies directly.
    That makes this a handy "production-like enough" smoke test for the
    task logic before doing any remote dispatch.
    """
    documents = [
        "Fast distributed python sdk",
        "Simple and secure platform",
        "Reliable distributed system",
        "Tiny local example",
    ]

    os.environ["TANDEM_WORKER"] = "1"

    try:
        token_lists = [tokenize(doc) for doc in documents]
        feature_maps = [extract_weighted_features(tokens) for tokens in token_lists]
        scores = score_many_feature_maps(feature_maps)
        labels = [label_score(score) for score in scores]
        summary = summarize_scores(scores)
    finally:
        os.environ.pop("TANDEM_WORKER", None)

    print("Local smoke test results:")
    for doc, score, label in zip(documents, scores, labels):
        print(f"  {doc!r} -> score={score:.2f}, label={label}")

    print("Summary:", summary)


def build_wasm_artifacts() -> None:
    """
    Uses the builder API directly.

    If this code is saved in a real Python file, __file__ lets the builder
    discover all decorated Tandem tasks in this module.
    """
    results = build_project(
        entry_path=__file__,
        build_dir=".tandem_build/smart-sdk-demo",
        toml_path="tandem.toml",
        on_task_start=lambda task_name: print(f"building {task_name}"),
        on_task_done=lambda result: print(
            f"built {result.task_name} -> {result.wasm_path} ({result.wasm_size} bytes)"
        ),
        on_task_error=lambda task_name, exc: print(
            f"failed to build {task_name}: {exc}"
        ),
    )

    for result in results:
        if result.warnings:
            print(f"warnings for {result.task_name}:")
            for warning in result.warnings:
                print(f"  - {warning}")


def remote_dispatch_example() -> None:
    """
    Once you have:
      - a tandem.toml in the current directory
      - built artifacts in the configured output directory
      - TANDEM_SERVER_URL set
      - TANDEM_API_KEY set
    ...then calling a @compute function without TANDEM_WORKER=1 will dispatch
    through tandem.rpc.dispatch_task(...).

    TANDEM_PID is optional. If present, the SDK reuses the existing deployment
    instead of creating a fresh one.
    """
    # Example call. In remote mode this goes through Tandem instead of running locally.
    result = label_score(0.82)
    print("Remote label:", result)


if __name__ == "__main__":
    try:
        local_smoke_test()

        # Uncomment this when running from a real module file and you want to build.
        # build_wasm_artifacts()

        # Uncomment this after you have a tandem.toml, built output,
        # and the needed env vars for the server.
        # remote_dispatch_example()

    except TandemValidationError as exc:
        print("Tandem validation error:", exc)
    except TandemBuildError as exc:
        print("Tandem build error:", exc)
