from __future__ import annotations

import argparse
import importlib
from pathlib import Path
import shutil


DEFAULT_MODELS = ["tiny", "base", "small", "medium", "large-v2", "large-v3"]
ALLOW_PATTERNS = [
    "config.json",
    "model.bin",
    "tokenizer.json",
    "vocabulary.*",
    "preprocessor_config.json",
]


def _configure_insecure_client() -> None:
    huggingface_hub = importlib.import_module("huggingface_hub")
    httpx = importlib.import_module("httpx")

    def _client_factory():
        return httpx.Client(verify=False, follow_redirects=True, trust_env=True)

    huggingface_hub.set_client_factory(_client_factory)
    if hasattr(huggingface_hub, "close_session"):
        huggingface_hub.close_session()


def _download_model(model_name: str, destination_root: Path, insecure: bool) -> None:
    huggingface_hub = importlib.import_module("huggingface_hub")
    repo_id = f"Systran/faster-whisper-{model_name}"
    local_dir = destination_root / model_name

    if insecure:
        _configure_insecure_client()

    if local_dir.exists():
        shutil.rmtree(local_dir)
    local_dir.mkdir(parents=True, exist_ok=True)

    print(f"[download-models] Downloading '{repo_id}' -> '{local_dir}'")
    huggingface_hub.snapshot_download(
        repo_id=repo_id,
        local_dir=str(local_dir),
        local_dir_use_symlinks=False,
        allow_patterns=ALLOW_PATTERNS,
    )
    print(f"[download-models] Ready: {local_dir}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Download local faster-whisper models for Dictly.")
    parser.add_argument("--dest", default="models", help="Destination folder for local model directories.")
    parser.add_argument(
        "--models",
        nargs="+",
        default=DEFAULT_MODELS,
        help="Model names to download. Defaults to all Dictly-supported models.",
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Disable TLS verification for Hugging Face downloads.",
    )
    args = parser.parse_args()

    destination_root = Path(args.dest).resolve()
    destination_root.mkdir(parents=True, exist_ok=True)

    for model_name in args.models:
        _download_model(model_name=model_name, destination_root=destination_root, insecure=args.insecure)

    print("[download-models] Done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
