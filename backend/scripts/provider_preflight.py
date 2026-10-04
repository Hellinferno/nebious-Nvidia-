"""Provider preflight (B-04): catalog discovery + one real bounded NVIDIA inference.

Fails explicitly (exit 1) when credentials are missing. Writes a sanitized
record (no key, no headers) to artifacts/preflight/provider_<timestamp>.json.

Usage:  python scripts/provider_preflight.py [--model MODEL_ID]
Env:    NEBIUS_API_KEY (required), NEBIUS_BASE_URL (optional), NEBIUS_MODEL_ID (optional)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

from benchproof.providers import NebiusAdapter, ProviderError

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = REPO_ROOT / "artifacts" / "preflight"


def pick_model(catalog: list[dict], requested: str | None) -> str | None:
    ids = [m["id"] for m in catalog]
    if requested:
        return requested if requested in ids else None
    nvidia = [i for i in ids if i.lower().startswith("nvidia/")]
    return nvidia[0] if nvidia else None


def _save(record: dict) -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    ts = record["timestamp"].replace(":", "").replace("-", "")[:15]
    path = ARTIFACT_DIR / f"provider_{ts}.json"
    path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(f"Saved {path.relative_to(REPO_ROOT)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model",
        default=None,
        help="exact model id; defaults to NEBIUS_MODEL_ID or the first nvidia/* catalog entry",
    )
    args = parser.parse_args()

    load_dotenv(REPO_ROOT / ".env")
    requested = args.model or os.getenv("NEBIUS_MODEL_ID") or None

    record: dict = {
        "schema_version": "benchproof/v2",
        "kind": "provider_preflight",
        "timestamp": datetime.now(UTC).isoformat(),
        "status": "BLOCKED",
    }

    try:
        adapter = NebiusAdapter()
    except ProviderError as e:
        record["blocker"] = str(e)
        print(f"BLOCKED: {e}. Set NEBIUS_API_KEY in {REPO_ROOT / '.env'} (see .env.example).")
        _save(record)
        return 1

    try:
        catalog = adapter.list_models()
    except ProviderError as e:
        record["blocker"] = str(e)
        print(f"BLOCKED: {e}")
        _save(record)
        return 1

    record["catalog_size"] = len(catalog)
    record["nvidia_models"] = sorted(
        m["id"] for m in catalog if m["id"].lower().startswith("nvidia/")
    )
    print(f"Catalog: {len(catalog)} models; NVIDIA-prefixed: {record['nvidia_models']}")

    model = pick_model(catalog, requested)
    if model is None:
        record["blocker"] = (
            f"requested model {requested!r} not in catalog"
            if requested
            else "no nvidia/* model in catalog"
        )
        print(f"BLOCKED: {record['blocker']}")
        _save(record)
        return 1
    record["selected_model"] = model
    # Manual step: record the model card / license URL in PROGRESS_LOG before relying on it.
    record["model_card_verified"] = False

    try:
        result = adapter.complete(
            model=model,
            system_prompt="You are a terse assistant.",
            user_prompt=(
                "Suggest one bounded check for a Python invoice-total rounding constraint. "
                "One sentence."
            ),
            max_tokens=128,
        )
    except ProviderError as e:
        record["blocker"] = str(e)
        print(f"BLOCKED: {e}")
        _save(record)
        return 1

    record["status"] = "OK"
    record["inference"] = result
    print(json.dumps(result, indent=2))
    _save(record)
    return 0


if __name__ == "__main__":
    sys.exit(main())
