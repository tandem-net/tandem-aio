import tandem

LABEL_MAP = tandem.immutable({0: "cat", 1: "dog", 2: "bird"})
SUPPORTED_FORMATS = tandem.constant(frozenset({"jpg", "png", "webp"}))


@tandem.compute
def validate_format(filename: str) -> bool:
    extension = filename.rsplit(".", 1)[-1].lower()
    return extension in SUPPORTED_FORMATS


@tandem.split(
    strategy="data_parallel", reducer="concat", max_shards=32, min_shard_size=50
)
def classify(images: list[int]) -> list[str]:
    return [LABEL_MAP[predict(image)] for image in images]


@tandem.pipeline(next="store_stage")
def normalize_stage(record: dict[str, str]) -> dict[str, str]:
    return {"text": record["text"].strip().lower()}


@tandem.compute
def store_stage(record: dict[str, str]) -> str:
    return record["text"]


@tandem.deferred(timeout_ms=60_000, result_ttl_seconds=3600)
def summarize(text: str) -> str:
    return text[:280]


@tandem.cron("0 0 * * *", timezone="UTC", allow_overlap=False)
def nightly_cleanup() -> None:
    return None


def predict(image: int) -> int:
    return image % len(LABEL_MAP)
