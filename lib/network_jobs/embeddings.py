"""Optional semantic (embedding) matching for network-jobs.

Everything here is best-effort and additive:

- No provider installed / reachable  ->  get_provider() returns None and every
  caller must degrade to today's keyword scoring with byte-identical scores.
- Nothing in this module may raise ImportError for a missing optional
  dependency. Lazy imports only; failures return None.
- Vectors are precomputed at refresh/rebuild time into corpus/embeddings.json.
  rank/discover/match never embed jobs -- they read the cache.
"""

from __future__ import annotations

import json
import math
import os
import urllib.request
from pathlib import Path
from typing import Any, Protocol

#: Default embedding model (ONNX, CPU-friendly, ~33-67MB quantized).
DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_DIMS = 384

#: Bump to invalidate the whole embeddings cache (embed-text recipe changed).
EMBED_RECIPE = 1

#: Cosine floors: at or below this, the semantic signal contributes nothing.
RESUME_SEMANTIC_FLOOR = 0.55
QUERY_SEMANTIC_FLOOR = 0.6

#: Max points the semantic signals can add.
RESUME_SEMANTIC_MAX = 4.0
QUERY_SEMANTIC_MAX = 2.0

EMBEDDINGS_FILE = "embeddings.json"
_BATCH_SIZE = 64
# Bound input length so one pathological JD can't blow up a batch.
_MAX_CHARS = 4000


class EmbeddingProvider(Protocol):
    name: str
    model: str
    dims: int

    def embed(self, texts: list[str]) -> list[list[float]] | None:
        """Embed a batch; None on any failure (never raises)."""
        ...


def embed_text_for(job: dict[str, Any]) -> str:
    """v1 recipe: title + department + description (when present)."""
    bits = [str(job.get("title") or ""), str(job.get("department") or "")]
    desc = str(job.get("description") or "").strip()
    if desc:
        bits.append(desc)
    return "\n".join(b for b in bits if b).strip()[:_MAX_CHARS]


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return max(-1.0, min(1.0, dot / (na * nb)))


def semantic_bonus(cos: float, floor: float, cap: float) -> float:
    """Map cosine similarity to [0, cap]; 0 at/below the floor."""
    if cos <= floor:
        return 0.0
    return round(min(1.0, (cos - floor) / (1.0 - floor)) * cap, 2)


class FastEmbedProvider:
    """fastembed (Qdrant): pip-installable ONNX embeddings, no torch."""

    name = "fastembed"
    model = DEFAULT_MODEL
    dims = DEFAULT_DIMS

    def __init__(self) -> None:
        # Import only -- the model (and its one-time download) happens lazily
        # on first embed(), never during provider detection.
        from fastembed import TextEmbedding  # noqa: F401

        self._model = None

    def _load(self):
        if self._model is None:
            from fastembed import TextEmbedding

            self._model = TextEmbedding(model_name=DEFAULT_MODEL)
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]] | None:
        try:
            model = self._load()
            out: list[list[float]] = []
            for i in range(0, len(texts), _BATCH_SIZE):
                batch = [t for t in texts[i : i + _BATCH_SIZE] if t]
                if not batch:
                    continue
                out.extend([list(map(float, v)) for v in model.embed(batch)])
            return out or None
        except Exception:
            return None


class OllamaProvider:
    """Local Ollama (http://localhost:11434), if the user already runs it."""

    name = "ollama"

    def __init__(self, base: str = "http://localhost:11434") -> None:
        self.base = base.rstrip("/")
        self.model = ""
        self.dims = 0

    def available(self) -> bool:
        try:
            with urllib.request.urlopen(
                self.base + "/api/tags", timeout=3
            ) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            names = [str(m.get("name") or "") for m in data.get("models", [])]
            for want, dims in (("nomic-embed-text", 768), ("all-minilm", 384)):
                if any(n == want or n.startswith(want + ":") for n in names):
                    self.model = want
                    self.dims = dims
                    return True
            return False
        except Exception:
            return False

    def embed(self, texts: list[str]) -> list[list[float]] | None:
        if not self.model:
            return None
        try:
            out: list[list[float]] = []
            for i in range(0, len(texts), _BATCH_SIZE):
                batch = [t for t in texts[i : i + _BATCH_SIZE] if t]
                if not batch:
                    continue
                payload = json.dumps({"model": self.model, "input": batch}).encode()
                req = urllib.request.Request(
                    self.base + "/api/embed",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=120) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                vecs = data.get("embeddings") or []
                out.extend([[float(x) for x in v] for v in vecs])
            return out or None
        except Exception:
            return None


def get_provider() -> EmbeddingProvider | None:
    """Best available provider, or None. Never raises, never downloads."""
    override = os.environ.get("NJ_EMBED_PROVIDER", "").strip().lower()
    if override == "none":
        return None
    if override in ("", "fastembed"):
        try:
            return FastEmbedProvider()
        except Exception:
            if override == "fastembed":
                return None
    if override in ("", "ollama"):
        try:
            ollama = OllamaProvider()
            if ollama.available():
                return ollama
        except Exception:
            pass
    return None


def embeddings_path(corpus_dir: Path) -> Path:
    return Path(corpus_dir) / EMBEDDINGS_FILE


def load_embeddings_cache(corpus_dir: Path) -> dict[str, Any]:
    """Return the embeddings.json payload, or {} when absent/unreadable."""
    try:
        data = json.loads(embeddings_path(corpus_dir).read_text())
        if isinstance(data, dict) and isinstance(data.get("vectors"), dict):
            return data
    except Exception:
        pass
    return {}


def maybe_update_embeddings(
    corpus_dir: Path,
    jobs: list[dict[str, Any]],
    provider: EmbeddingProvider | None = None,
) -> dict[str, Any]:
    """Embed new/changed jobs into corpus/embeddings.json.

    Incremental: only fingerprints missing from the cache are embedded.
    A model or recipe change re-embeds everything; fingerprints that left the
    corpus are pruned. No provider -> no-op, cache untouched.
    """
    if provider is None:
        provider = get_provider()
    if provider is None:
        return {"updated": False, "reason": "no-provider"}

    cache = load_embeddings_cache(corpus_dir)
    vectors: dict[str, list[float]] = dict(cache.get("vectors") or {})
    full_refresh = (
        cache.get("model") != provider.model or cache.get("recipe") != EMBED_RECIPE
    )

    fps: dict[str, dict[str, Any]] = {}
    for job in jobs:
        fp = str(job.get("fingerprint") or "")
        if fp:
            fps[fp] = job

    if full_refresh:
        todo = list(fps.items())
    else:
        todo = [(fp, job) for fp, job in fps.items() if fp not in vectors]

    embedded = 0
    if todo:
        texts = [embed_text_for(job) for _, job in todo]
        idx = [i for i, t in enumerate(texts) if t]
        vecs = provider.embed([texts[i] for i in idx]) if idx else []
        if vecs is None:
            return {"updated": False, "reason": "embed-failed"}
        for pos, v in zip(idx, vecs):
            vectors[todo[pos][0]] = v
            embedded += 1

    pruned = 0
    for fp in list(vectors):
        if fp not in fps:
            del vectors[fp]
            pruned += 1

    payload = {
        "model": provider.model,
        "dims": provider.dims,
        "recipe": EMBED_RECIPE,
        "vectors": vectors,
    }
    embeddings_path(corpus_dir).write_text(json.dumps(payload) + "\n")
    return {
        "updated": True,
        "model": provider.model,
        "embedded": embedded,
        "pruned": pruned,
        "total": len(vectors),
        "fullRefresh": full_refresh,
    }
