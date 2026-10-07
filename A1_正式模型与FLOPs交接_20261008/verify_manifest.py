"""Verify the delivered files without importing ML packages."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent
manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
for entry in manifest["files"]:
    path = (root/entry["path"]).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Manifest path escapes handoff root")
    if path.stat().st_size != entry["size_bytes"] or hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
        raise ValueError(f"File mismatch: {entry['path']}")
print(f"PASS: {len(manifest['files'])} files verified")
