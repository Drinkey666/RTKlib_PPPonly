"""Verify and unpack one published evidence case for the recorded PC replay."""

import argparse
import gzip
import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def restore(catalog, case, destination):
    archives = {entry["archive"]: entry for entry in catalog["files"]}
    inputs = {}
    for role, relative_path in catalog["runs"][case].items():
        entry = archives[relative_path]
        archive = ROOT / relative_path
        if sha256(archive) != entry["sha256_gzip"]:
            raise ValueError(f"Archive SHA-256 mismatch: {archive}")

        output = destination / archive.stem
        if not output.exists():
            with gzip.open(archive, "rb") as source, output.open("xb") as target:
                shutil.copyfileobj(source, target)
        if sha256(output) != entry["sha256_unpacked"]:
            raise ValueError(f"Input SHA-256 mismatch: {output}")
        inputs[role] = str(output)

    manifest = destination / "manifest.json"
    with manifest.open("x", encoding="utf-8") as stream:
        json.dump({"source": "txt-fast", "usage": "ARCHIVED_REGRESSION", "files": inputs}, stream, indent=2)
        stream.write("\n")
    return manifest


def main():
    catalog = json.loads((ROOT / "validation" / "PROJECT_DATA_MANIFEST.json").read_text(encoding="utf-8"))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", choices=sorted(catalog["runs"]))
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    destination = args.destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    print(restore(catalog, args.case, destination))


if __name__ == "__main__":
    main()
