from __future__ import annotations

"""Minimal Flask app demonstrating Tandem SDK decorators.

Run locally:

    cd tandem-aio/sdk/python-sdk
    pip install -e .
    pip install flask
    python examples/flask_app.py

Example requests:

    curl http://127.0.0.1:5000/health

    curl -X POST http://127.0.0.1:5000/normalize \
      -H "Content-Type: application/json" \
      -d '{"text":"The platform is fast and reliable"}'

    curl -X POST http://127.0.0.1:5000/classify \
      -H "Content-Type: application/json" \
      -d '{"texts":["Fast reliable api", "Buggy slow worker"]}'
"""

from flask import Flask, jsonify, request

import tandem

STOP_WORDS = tandem.immutable({"the", "a", "an", "and", "or", "but"})
POSITIVE_WORDS = tandem.immutable(
    {"fast", "reliable", "clean", "excellent", "great", "stable"}
)
NEGATIVE_WORDS = tandem.immutable(
    {"slow", "buggy", "broken", "bad", "error", "unstable"}
)
CATEGORY_KEYWORDS = tandem.immutable(
    {
        "performance": {"fast", "slow", "latency", "throughput"},
        "quality": {"buggy", "broken", "stable", "reliable", "clean"},
        "ops": {"deploy", "server", "worker", "queue", "api"},
    }
)


@tandem.compute(batch=4, timeout_ms=25)
def normalize_text(text: str) -> dict[str, object]:
    cleaned = " ".join(text.strip().lower().split())
    tokens = [token.strip(".,!?") for token in cleaned.split() if token]
    filtered_tokens = [token for token in tokens if token and token not in STOP_WORDS]
    return {
        "original": text,
        "normalized": " ".join(filtered_tokens),
        "token_count": len(filtered_tokens),
    }


@tandem.compute(batch=4, timeout_ms=25)
def score_text(text: str) -> dict[str, object]:
    normalized = normalize_text(text)
    tokens = str(normalized["normalized"]).split()
    positive = sum(1 for token in tokens if token in POSITIVE_WORDS)
    negative = sum(1 for token in tokens if token in NEGATIVE_WORDS)
    sentiment = "neutral"
    if positive > negative:
        sentiment = "positive"
    elif negative > positive:
        sentiment = "negative"

    return {
        "normalized": normalized["normalized"],
        "positive_hits": positive,
        "negative_hits": negative,
        "sentiment": sentiment,
    }


def classify_single(text: str) -> dict[str, object]:
    normalized = normalize_text(text)
    tokens = set(str(normalized["normalized"]).split())

    category_scores = {
        category: len(tokens & keywords)
        for category, keywords in CATEGORY_KEYWORDS.items()
    }
    best_category = max(category_scores, key=category_scores.get)

    return {
        "text": text,
        "normalized": normalized["normalized"],
        "category": best_category if category_scores[best_category] > 0 else "general",
        "matches": category_scores,
    }


classify_many = tandem.split(classify_single, chunk=8)


def _json_body() -> dict[str, object]:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return {}
    return payload


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/health")
    def health() -> tuple[dict[str, object], int]:
        return {
            "ok": True,
            "service": "tandem-sdk-flask-example",
            "decorated_functions": ["normalize_text", "score_text", "classify_many"],
        }, 200

    @app.post("/normalize")
    def normalize_route() -> tuple[dict[str, object], int]:
        payload = _json_body()
        text = str(payload.get("text") or "").strip()
        if not text:
            return {"error": "Request JSON must include a non-empty `text` field."}, 400
        return jsonify(normalize_text(text)), 200

    @app.post("/score")
    def score_route() -> tuple[dict[str, object], int]:
        payload = _json_body()
        text = str(payload.get("text") or "").strip()
        if not text:
            return {"error": "Request JSON must include a non-empty `text` field."}, 400
        return jsonify(score_text(text)), 200

    @app.post("/classify")
    def classify_route() -> tuple[dict[str, object], int]:
        payload = _json_body()
        raw_texts = payload.get("texts")
        if not isinstance(raw_texts, list) or not raw_texts:
            return {"error": "Request JSON must include a non-empty `texts` list."}, 400

        texts = [str(item).strip() for item in raw_texts if str(item).strip()]
        if not texts:
            return {
                "error": "Request JSON `texts` list must contain at least one non-empty value."
            }, 400

        return jsonify({"results": classify_many(texts)}), 200

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
