"""Fixed input tensors for `--model-only` measurement (§5 of the A4 contract).

A4's runtime exposes a model-only mode that must be driven with the *same*
tensors the deployed preprocessing produces, not with re-derived ones.  B3 owns
that side: this module runs A1's `StudentPreprocessor` on a request, stores the
four tensors as `.npy` files plus a manifest, and can load them back and check
their digests.

The dump is deliberately boring on purpose:

* the manifest records shape, dtype and SHA256 of every tensor file, so B2 can
  recompute the run from the files alone;
* the request that produced the dump is recorded by canonical digest, so a
  "which request is this?" question never needs a guess;
* loading verifies the recorded digests before handing anything to a runtime.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .identity import sha256_file
from .run_io import write_json


TENSOR_NAMES: tuple[str, ...] = ("rgb", "text_tokens", "targets", "state")
DUMP_SCHEMA_VERSION = "1.0"


def canonical_sha256(payload: Any) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def dump_tensors_for_request(
    repo_root: str | Path,
    request: Mapping[str, Any],
    out_dir: str | Path,
    *,
    case_id: str | None = None,
    frame_label: str | None = None,
) -> dict[str, Any]:
    """Write `rgb/text_tokens/targets/state` `.npy` files plus `manifest.json`."""
    import numpy

    # Imported lazily so a machine without torch can still read dumps.
    from .runtime_adapter import _RepoModules

    modules = _RepoModules(repo_root)
    StudentPreprocessor = modules.get("challenge.student.preprocess.StudentPreprocessor")
    StudentPlannerV0 = modules.get("challenge.student.model.StudentPlannerV0")
    contract = StudentPlannerV0().contract
    preprocessor = StudentPreprocessor(contract)
    tensorized = preprocessor(request)

    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    files: dict[str, dict[str, Any]] = {}
    for name in TENSOR_NAMES:
        array = getattr(tensorized, name).detach().to("cpu").contiguous().numpy()
        path = target / f"{name}.npy"
        numpy.save(path, array)
        files[path.name] = {
            "shape": list(array.shape),
            "dtype": str(array.dtype),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }

    manifest = {
        "schema_version": DUMP_SCHEMA_VERSION,
        "case_id": case_id,
        "frame_label": frame_label,
        "request_sha256": canonical_sha256(dict(request)),
        "request_id": request.get("request_id"),
        "command_id": request.get("command_id"),
        "tensor_order": list(TENSOR_NAMES),
        "files": files,
        "notes": (
            "Tensors produced by A1's StudentPreprocessor on this host. A4's "
            "--model-only mode is expected to load exactly these files so its "
            "raw-output checksum can be compared with the X86/ONNX checksum."
        ),
    }
    write_json(target / "manifest.json", manifest)
    return manifest


def load_tensor_dump(path: str | Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load a dump, verifying every recorded digest first."""
    import numpy

    root = Path(path)
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"no tensor dump manifest at {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = manifest.get("files")
    if not isinstance(files, Mapping):
        raise ValueError(f"{manifest_path} has no files section")
    arrays: dict[str, Any] = {}
    for name in TENSOR_NAMES:
        entry = files.get(f"{name}.npy")
        if not isinstance(entry, Mapping):
            raise ValueError(f"tensor dump is missing {name}.npy")
        tensor_path = root / f"{name}.npy"
        actual = sha256_file(tensor_path)
        if str(entry.get("sha256", "")).lower() != actual.lower():
            raise ValueError(
                f"{tensor_path.name} changed since it was dumped: {actual}"
            )
        arrays[name] = numpy.load(tensor_path)
    return arrays, manifest


def output_checksums(outputs: Mapping[str, Any]) -> dict[str, Any]:
    """Per-output SHA256 over the raw bytes, for cross-machine comparison."""
    digests: dict[str, str] = {}
    for name, value in sorted(outputs.items()):
        array = value
        if hasattr(array, "detach"):
            array = array.detach().to("cpu").contiguous().numpy()
        if hasattr(array, "tobytes"):
            digest = hashlib.sha256(memoryview(array.tobytes())).hexdigest()
        else:
            digest = hashlib.sha256(repr(array).encode("utf-8")).hexdigest()
        digests[str(name)] = digest
    return digests


__all__ = [
    "DUMP_SCHEMA_VERSION",
    "TENSOR_NAMES",
    "canonical_sha256",
    "dump_tensors_for_request",
    "load_tensor_dump",
    "output_checksums",
]
