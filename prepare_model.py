"""Download exactly the model revision declared by an experiment configuration."""
import argparse
import json
import re
from pathlib import Path

from huggingface_hub import snapshot_download


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/pilot-v2.json")
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    revision = config["model_revision"]
    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise SystemExit("Set model_revision to an explicit 40-character commit hash before downloading")
    path = snapshot_download(config["model_id"], revision=revision,
                             allow_patterns=["*.json", "*.safetensors", "*.txt", "*.jinja"])
    print(path)


if __name__ == "__main__":
    main()
