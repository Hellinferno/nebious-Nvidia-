"""Provider preflight (B-04): catalog discovery, one real bounded NVIDIA inference,
and one structured-JSON capability check.

Fails explicitly (exit 1) when credentials are missing. Writes a sanitized
record (no key, no headers) to artifacts/preflight/provider_<timestamp>.json
and prints the exact .env lines to pin the tested endpoint and model.

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

from benchproof.constraints import list_constraints
from benchproof.providers import NebiusAdapter, ProviderError

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = REPO_ROOT / "artifacts" / "preflight"

# Documented Token Factory URL first (docs/07); the older Studio hostname is a known alias.
KNOWN_BASE_URLS = [
    "https://api.tokenfactory.nebius.com/v1/",
    "https://api.studio.nebius.com/v1/",
]


def pick_model(catalog: list[dict], requested: str | None) -> str | None:
    ids = [m["id"] for m in catalog]
    if requested:
        return requested if requested in ids else None
    nvidia = sorted(i for i in ids if i.lower().startswith("nvidia/"))
    return nvidia[0] if nvidia else None


def _save(record: dict) -> Path:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    ts = record["timestamp"].replace(":", "").replace("-", "")[:15]
    path = ARTIFACT_DIR / f"provider_{ts}.json"
    path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(f"Saved {path.relative_to(REPO_ROOT)}")
    return path


def _blocked(record: dict, reason: str) -> int:
    record["status"] = "BLOCKED"
    record["blocker"] = reason
    print(f"BLOCKED: {reason}")
    _save(record)
    return 1


def connect(record: dict) -> tuple[NebiusAdapter, list[dict]] | None:
    """Try the configured base URL, or each known URL, until the catalog answers."""
    configured = os.getenv("NEBIUS_BASE_URL", "").strip()
    candidates = [configured] if configured else KNOWN_BASE_URLS
    record["endpoint_attempts"] = []
    for url in candidates:
        try:
            adapter = NebiusAdapter(base_url=url)
            catalog = adapter.list_models()
        except ProviderError as e:
            record["endpoint_attempts"].append({"base_url": url, "ok": False, "error": str(e)})
            continue
        record["endpoint_attempts"].append({"base_url": url, "ok": True, "models": len(catalog)})
        record["base_url"] = url
        return adapter, catalog
    return None


def structured_check(adapter: NebiusAdapter, model: str) -> dict:
    """Ask for a constraint-linked JSON action and validate it server-side."""
    allowed = sorted({cid for c in list_constraints() for cid in c.protected_check_ids})
    system = (
        "You propose exactly one protected check to run. Reply with JSON only, shaped as "
        '{"check_id": string, "reason": string}. check_id must be one of: ' + ", ".join(allowed)
    )
    user = (
        "A Python invoice service rounds each line amount before summing. "
        "Which single protected check should run first?"
    )
    out: dict = {"supported": False, "valid": False, "allowed_check_ids": allowed}
    try:
        res = adapter.complete(
            model=model,
            system_prompt=system,
            user_prompt=user,
            max_tokens=512,  # reasoning models spend tokens before the JSON; 128 truncated
            response_format={"type": "json_object"},
        )
    except ProviderError as e:
        out["error"] = str(e)
        return out
    out["supported"] = True
    out["raw"] = res["content"]
    out["finish_reason"] = res["finish_reason"]
    out["usage"] = res["usage"]
    out["elapsed_ms"] = res["elapsed_ms"]
    try:
        parsed = json.loads(res["content"])
        out["valid"] = isinstance(parsed, dict) and parsed.get("check_id") in allowed
        out["parsed"] = parsed if isinstance(parsed, dict) else None
        if not out["valid"]:
            out["rejection"] = "check_id missing or not in the allowed set"
    except json.JSONDecodeError as e:
        out["rejection"] = f"malformed JSON: {e.msg}"
    return out


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
        NebiusAdapter()  # credential presence check only
    except ProviderError as e:
        return _blocked(record, f"{e}. Set NEBIUS_API_KEY in {REPO_ROOT / '.env'}")

    connected = connect(record)
    if connected is None:
        return _blocked(record, "no configured or known endpoint returned a model catalog")
    adapter, catalog = connected

    record["catalog_size"] = len(catalog)
    record["nvidia_models"] = sorted(
        m["id"] for m in catalog if m["id"].lower().startswith("nvidia/")
    )
    print(f"Endpoint {record['base_url']} — {len(catalog)} models")
    print("NVIDIA-prefixed models:")
    for mid in record["nvidia_models"] or ["(none)"]:
        print(f"  - {mid}")

    model = pick_model(catalog, requested)
    if model is None:
        reason = (
            f"requested model {requested!r} not in catalog"
            if requested
            else "no nvidia/* model in catalog; pass --model with an id from the list above"
        )
        return _blocked(record, reason)
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
            max_tokens=512,  # reasoning model: 128 left no visible content
        )
    except ProviderError as e:
        return _blocked(record, str(e))

    record["status"] = "OK"
    record["inference"] = result
    print(f"\nInference OK on {result['response_model'] or model} in {result['elapsed_ms']} ms; "
          f"usage {result['usage']}")
    print(f"Reply: {result['content'].strip()[:300]}")

    record["structured_output"] = structured_check(adapter, model)
    so = record["structured_output"]
    if so["supported"]:
        verdict = "valid" if so["valid"] else f"rejected ({so.get('rejection')})"
        print(f"Structured JSON: supported; proposal {verdict}")
    else:
        print(f"Structured JSON: not supported on this model ({so.get('error')})")

    _save(record)
    print("\nPin the tested configuration in .env:")
    print(f"  NEBIUS_BASE_URL={record['base_url']}")
    print(f"  NEBIUS_MODEL_ID={model}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
