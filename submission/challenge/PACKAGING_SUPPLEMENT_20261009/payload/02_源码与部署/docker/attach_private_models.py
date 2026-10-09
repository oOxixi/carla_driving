#!/usr/bin/env python3
"""Append verified local ONNX weights to an observed Docker save runtime stage.

This does not execute Docker, publish weights, or create a submission ZIP.
The result is a legacy manifest.json Docker archive accepted by docker load.
Only model file attachment is asserted; final Linux load/inference stays pending.
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import tarfile
import zlib

CHUNK = 1024 * 1024
MAX_JSON = 4 * CHUNK
MAX_CANDIDATE_JSON = 32 * CHUNK
EXPECTED_STAGE_STATUS = "RUNTIME_STAGE_BUILT_VERIFIED_EXPORTED_WITHOUT_PRIVATE_MODELS"
EXPECTED_CORE = {"torch": "2.8.0+cpu", "onnxruntime": "1.19.0", "numpy": "1.23.0",
                 "Pillow": "9.3.0", "jsonschema": "4.25.1", "psutil": "7.2.1"}
MODEL_SPECS = (
    ("full_int8", "03_训练与模型/A2模型与量化/models/full_int8/student_int8.onnx",
     23273686, "275dce5c426fff85a0375eb286fc67febac8d835c1e36fe15b0fbd707cf836c3"),
    ("fp32_candidate", "03_训练与模型/A2模型与量化/models/student_v0_fp32_candidate.onnx",
     92041414, "681a5d4bf16ba61741ef0e559649c43c041de649eef3e8e6f0b6285beaab4286"),
    ("mixed_precision_top3", "03_训练与模型/A2模型与量化/models/mixed_precision_top3/student_int8_mixed_top3.onnx",
     23622853, "9a08a03c42a9ea59ead664d168254cd3685d73d176d5ab53507bd4a4467132d3"),
)
SHA = re.compile(r"^[0-9a-f]{64}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
TAG = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*(?:/[a-z0-9]+(?:[._-][a-z0-9]+)*)*:[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$")


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def json_bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def file_sha(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(CHUNK * 8):
            result.update(block)
    return result.hexdigest()


def safe_archive_path(name, directory=False):
    require(isinstance(name, str) and bool(name), "Empty/non-string Docker archive path")
    cleaned = name[:-1] if directory and name.endswith("/") else name
    require(cleaned and "\\" not in cleaned and "\x00" not in cleaned,
            f"Invalid Docker archive path: {name!r}")
    require(not cleaned.startswith("/") and not re.match(r"^[A-Za-z]:", cleaned),
            f"Absolute Docker archive path: {name!r}")
    parts = cleaned.split("/")
    require(all(part and part not in (".", "..") for part in parts),
            f"Non-canonical/traversing Docker archive path: {name!r}")
    return cleaned


def read_json(path):
    require(path.is_file() and not path.is_symlink(), f"Missing/non-regular metadata: {path}")
    require(path.stat().st_size <= MAX_JSON, f"Metadata too large: {path.name}")
    with path.open("r", encoding="utf-8-sig") as stream:
        return json.load(stream)


def inspect_archive(archive):
    """One bounded-memory metadata scan; no image tree is extracted to disk."""
    members, candidates = {}, {}
    candidate_bytes = 0
    with tarfile.open(archive, "r|gz") as tar:
        for member in tar:
            name = safe_archive_path(member.name, member.isdir())
            require(member.isdir() or member.isfile(), f"Unsupported outer tar link/type: {name}")
            require(name not in members, f"Duplicate outer archive entry: {name}")
            require(member.size >= 0, f"Negative entry size: {name}")
            members[name] = {"size": member.size, "file": member.isfile()}
            if not member.isfile():
                continue
            possible_json = name == "manifest.json" or bool(re.fullmatch(r"[0-9a-f]{64}\.json", name)) \
                or bool(re.fullmatch(r"blobs/sha256/[0-9a-f]{64}", name))
            if not possible_json or member.size > MAX_JSON:
                continue
            stream = tar.extractfile(member)
            require(stream is not None, f"Cannot read archive metadata: {name}")
            prefix = stream.read(min(member.size, 512))
            if prefix.lstrip()[:1] not in (b"{", b"["):
                continue
            data = prefix + stream.read()
            require(len(data) == member.size, f"Truncated metadata: {name}")
            candidate_bytes += len(data)
            require(candidate_bytes <= MAX_CANDIDATE_JSON, "Too much JSON metadata in Docker archive")
            candidates[name] = data
    require("manifest.json" in candidates, "Docker save manifest.json is missing")
    manifest = json.loads(candidates["manifest.json"])
    require(isinstance(manifest, list) and len(manifest) == 1,
            "Expected exactly one exported runtime stage image")
    entry = manifest[0]
    require(isinstance(entry, dict), "Invalid Docker image manifest entry")
    config_path = safe_archive_path(entry.get("Config"))
    require(config_path in candidates, "Docker config missing/too large/not JSON")
    config_bytes = candidates[config_path]
    config = json.loads(config_bytes)
    layers = entry.get("Layers")
    require(isinstance(layers, list) and 1 <= len(layers) <= 256, "Invalid layer list/count")
    layers = [safe_archive_path(layer) for layer in layers]
    require(all(layer in members and members[layer]["file"] for layer in layers),
            "Missing or non-regular referenced layer")
    require(config_path not in layers and "manifest.json" not in layers, "Layer/metadata path collision")
    return entry, config_bytes, config, layers, members


def verify_stage(archive, metadata_path, expected_commit):
    metadata = read_json(metadata_path)
    require(metadata.get("status") == EXPECTED_STAGE_STATUS, "Runtime stage export has not completed")
    require(COMMIT.fullmatch(expected_commit) is not None, "Expected commit must be 40 lowercase hex characters")
    require(metadata.get("source_commit") == expected_commit, "Runtime stage source commit mismatch")
    for key, expected in (("private_model_files_included", False), ("runtime_dependency_check_run", True),
                          ("runtime_import_check_run", True), ("model_inference_run", False),
                          ("final_student_image_built", False), ("registry_published", False)):
        require(metadata.get(key) is expected, f"Stage metadata flag mismatch: {key}")
    require(metadata.get("archive_file") == archive.name, "Runtime archive filename mismatch")
    require(metadata.get("archive_bytes") == archive.stat().st_size, "Runtime archive size mismatch")
    expected_sha = metadata.get("archive_sha256", "")
    require(SHA.fullmatch(expected_sha) is not None, "Invalid stage archive SHA256")
    print("Hashing observed runtime archive...", flush=True)
    require(file_sha(archive) == expected_sha, "Runtime stage archive SHA256 mismatch")
    sidecars = metadata_path.parent
    inspect = read_json(sidecars / "image_inspect.json")
    require(isinstance(inspect, list) and len(inspect) == 1, "Invalid actual Docker image inspect")
    inspect = inspect[0]
    deps = read_json(sidecars / "runtime_dependencies.json")
    require(deps.get("status") == "RUNTIME_STAGE_VERIFIED_WITHOUT_MODEL_FILES",
            "Actual runtime dependency verification missing/failed")
    require(deps.get("python") == "3.10.12", "Runtime Python baseline mismatch")
    for name, version in EXPECTED_CORE.items():
        require(deps.get("packages", {}).get(name) == version, f"Runtime dependency mismatch: {name}")
    yaml = deps.get("packages", {}).get("PyYAML", "")
    require(re.match(r"^6\.\d+", yaml) is not None, "Runtime PyYAML baseline range mismatch")
    require(deps.get("private_model_files_included") is False and deps.get("model_inference_run") is False,
            "Runtime stage dependency metadata incorrectly claims model verification")
    status = read_json(sidecars / "build_status.json")
    require(status.get("status") == "RUNTIME_STAGE_EXPORTED" and status.get("exit_code") == 0,
            "Remote runtime stage did not finish successfully")
    context = read_json(sidecars / "public_context_check.json")
    require(context.get("status") == "PASS" and context.get("private_model_files_included") is False,
            "Public runtime context validation failed")
    registry = read_json(sidecars / "registry_metadata.json")
    base_inspect = read_json(sidecars / "base_image_inspect.json")
    require(isinstance(base_inspect, list) and len(base_inspect) == 1, "Invalid actual base image inspect")
    base_inspect = base_inspect[0]
    require(metadata.get("base_ref") == registry.get("base_tag") and
            metadata.get("resolved_base") == registry.get("resolved_base"), "Actual runtime base identity mismatch")
    require(metadata.get("base_image_id") == base_inspect.get("Id"), "Base image config ID mismatch")
    require(base_inspect.get("Architecture") == "amd64" and base_inspect.get("Os") == "linux",
            "Actual base image is not Linux amd64")
    resolved_base = metadata.get("resolved_base", "")
    require(isinstance(resolved_base, str) and "@sha256:" in resolved_base and
            SHA.fullmatch(resolved_base.rsplit("@sha256:", 1)[1]) is not None,
            "Runtime base is not recorded as an immutable registry digest")
    resolved_digest = resolved_base.rsplit("@", 1)[1]
    base_repo_digests = base_inspect.get("RepoDigests") or []
    require(any(isinstance(value, str) and value.rsplit("@", 1)[-1] == resolved_digest
                for value in base_repo_digests), "Actual base image inspect does not contain the resolved digest")
    require(metadata.get("base_repo_digests") == base_repo_digests,
            "Base repo digest metadata/inspect mismatch")
    require(isinstance(metadata.get("base_kind"), str) and
            isinstance(metadata.get("official_environment_equivalent"), bool),
            "Missing explicit official/self-built base classification")
    for key in ("base_kind", "official_environment_equivalent", "official_base_ref", "official_base_access"):
        require(metadata.get(key) == registry.get(key), f"Registry/stage base classification mismatch: {key}")
    if metadata["base_kind"] == "PUBLIC_X86_PINNED_RUNTIME":
        require(metadata["official_environment_equivalent"] is False,
                "Self-built public X86 runtime cannot claim official environment equivalence")
    print("Reading Docker archive metadata...", flush=True)
    entry, config_bytes, config, layers, members = inspect_archive(archive)
    image_id = "sha256:" + hashlib.sha256(config_bytes).hexdigest()
    require(metadata.get("image_id") == image_id == inspect.get("Id"), "Actual Docker stage config identity mismatch")
    config_name = entry["Config"]
    require(config_name in (image_id[7:] + ".json", "blobs/sha256/" + image_id[7:]),
            "Config archive path does not match its content digest")
    require(config.get("os") == inspect.get("Os") == "linux" and
            config.get("architecture") == inspect.get("Architecture") == "amd64",
            "Runtime stage must be Linux amd64")
    rootfs = config.get("rootfs", {})
    diff_ids = rootfs.get("diff_ids")
    require(rootfs.get("type") == "layers" and isinstance(diff_ids, list) and len(diff_ids) == len(layers),
            "Docker rootfs diff_ids/layer count mismatch")
    require(all(isinstance(digest, str) and digest.startswith("sha256:") and
                SHA.fullmatch(digest[7:]) for digest in diff_ids), "Invalid rootfs diff_id")
    require(diff_ids == metadata.get("image_rootfs_diff_ids") == inspect.get("RootFS", {}).get("Layers"),
            "Stage metadata/Docker inspect/config rootfs mismatch")
    base_diff_ids = base_inspect.get("RootFS", {}).get("Layers")
    require(isinstance(base_diff_ids, list) and bool(base_diff_ids) and
            diff_ids[:len(base_diff_ids)] == base_diff_ids, "Runtime stage does not inherit the recorded base rootfs")
    layer_expected = {}
    for path, digest in zip(layers, diff_ids):
        require(path not in layer_expected or layer_expected[path] == digest,
                "Same exported layer is referenced with different diff_ids")
        layer_expected[path] = digest
    labels = config.get("config", {}).get("Labels", {})
    require(labels.get("challenge.artifact_kind") == "runtime_stage_without_private_models",
            "This archive is not the prepared private-weight-free runtime stage")
    require(inspect.get("Config", {}).get("Labels", {}).get("challenge.artifact_kind") ==
            "runtime_stage_without_private_models", "Actual image inspect stage label mismatch")
    require(metadata.get("image_ref") in (entry.get("RepoTags") or []), "Stage image tag identity mismatch")
    runtime_config = config.get("config", {})
    require(runtime_config.get("WorkingDir") == "/opt/challenge", "Unexpected stage working directory")
    require(runtime_config.get("Entrypoint") == ["python3", "/opt/challenge/02_源码与部署/scripts/launch_student.py"],
            "Unexpected Student service entrypoint")
    require(runtime_config.get("Cmd") == ["--mode", "http", "--variant", "full_int8", "--host", "0.0.0.0", "--port", "8100"],
            "Unexpected default Student variant/service command")
    history = config.get("history")
    require(isinstance(history, list) and all(isinstance(item, dict) for item in history) and
            sum(not item.get("empty_layer", False) for item in history) == len(layers),
            "Docker history/rootfs layer count mismatch")
    return metadata, config, layers, members, layer_expected


def verify_models(package_root):
    verified = []
    for variant, relative, size, digest in MODEL_SPECS:
        unresolved = package_root / relative
        require(unresolved.is_file() and not unresolved.is_symlink(), f"Missing/linked formal model: {relative}")
        path = unresolved.resolve()
        require(path.is_relative_to(package_root), f"Model resolves outside package: {relative}")
        require(path.stat().st_size == size, f"Formal model size mismatch: {variant}")
        require(file_sha(path) == digest, f"Formal model SHA256 mismatch: {variant}")
        verified.append({"variant": variant, "source_path": path, "package_relative_path": relative,
                         "container_path": "opt/challenge/" + relative, "bytes": size, "sha256": digest})
    return verified


def tar_info(name, size=0, directory=False):
    item = tarfile.TarInfo(name)
    item.size = size
    item.uid = item.gid = 0
    item.uname = item.gname = "root"
    item.mode = 0o755 if directory else 0o644
    item.mtime = 0
    if directory:
        item.type = tarfile.DIRTYPE
    return item


class DigestReader:
    """Hash the exact bytes passed to tarfile.addfile."""
    def __init__(self, stream):
        self.stream = stream
        self.sha = hashlib.sha256()
        self.count = 0

    def read(self, size=-1):
        block = self.stream.read(size)
        self.sha.update(block)
        self.count += len(block)
        return block


class LayerReader(DigestReader):
    """Preserve raw layer bytes while hashing their uncompressed rootfs diff_id."""
    def __init__(self, stream):
        super().__init__(stream)
        self.diff_sha = hashlib.sha256()
        self.compression = None
        self.decoder = None

    def read(self, size=-1):
        block = super().read(size)
        if not block:
            return block
        if self.compression is None:
            if block.startswith(b"\x1f\x8b"):
                self.compression = "gzip"
                self.decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
            else:
                require(not block.startswith((b"BZh", b"\xfd7zXZ", b"\x28\xb5\x2f\xfd")),
                        "Unsupported bzip2/xz/zstd layer; no output will be accepted")
                self.compression = "uncompressed"
        if self.compression == "uncompressed":
            self.diff_sha.update(block)
        else:
            self._gzip_hash(block)
        return block

    def _gzip_hash(self, block):
        # Bounded-memory decompression also validates each gzip CRC/footer.
        while block:
            if self.decoder.eof:
                self.decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
            expanded = self.decoder.decompress(block, CHUNK)
            self.diff_sha.update(expanded)
            block = self.decoder.unused_data if self.decoder.eof else self.decoder.unconsumed_tail

    def finish(self):
        require(self.compression is not None, "Empty Docker filesystem layer")
        if self.compression == "gzip":
            require(self.decoder.eof, "Truncated gzip Docker layer")
        return "sha256:" + self.diff_sha.hexdigest()


class DigestWriter:
    def __init__(self, stream):
        self.stream = stream
        self.sha = hashlib.sha256()
        self.count = 0

    def write(self, block):
        written = self.stream.write(block)
        require(written == len(block), "Short write during Docker archive export")
        self.sha.update(block)
        self.count += written
        return written

    def flush(self):
        self.stream.flush()


def build_model_layer(target, models):
    directories = {str(parent) for model in models
                   for parent in PurePosixPath(model["container_path"]).parents if str(parent) != "."}
    with target.open("xb") as raw, tarfile.open(fileobj=raw, mode="w|", format=tarfile.PAX_FORMAT) as tar:
        for directory in sorted(directories, key=lambda value: (value.count("/"), value)):
            tar.addfile(tar_info(directory, directory=True))
        for model in models:
            with model["source_path"].open("rb") as source:
                hashed = DigestReader(source)
                tar.addfile(tar_info(model["container_path"], model["bytes"]), hashed)
                require(hashed.count == model["bytes"] and hashed.sha.hexdigest() == model["sha256"],
                        f"Model changed while assembling layer: {model['variant']}")
                require(not source.read(1), f"Model grew while assembling layer: {model['variant']}")
    return "sha256:" + file_sha(target)


def make_final_config(stage_config, metadata, models, new_diff_id, created):
    config = copy.deepcopy(stage_config)
    config["created"] = created
    config["rootfs"]["diff_ids"].append(new_diff_id)
    config["history"].append({"created": created,
        "created_by": "attach_private_models.py: append locally SHA256-verified formal ONNX models",
        "comment": "Private models attached locally; final Linux docker load and ONNX inference are pending"})
    labels = config["config"].setdefault("Labels", {})
    labels.update({"challenge.artifact_kind": "student_x86_private_models_attached",
        "challenge.runtime_stage.image_id": metadata["image_id"],
        "challenge.runtime_stage.source_commit": metadata["source_commit"],
        "challenge.runtime_stage.archive_sha256": metadata["archive_sha256"],
        "challenge.runtime_base.kind": metadata["base_kind"],
        "challenge.official_environment_equivalent": str(metadata["official_environment_equivalent"]).lower(),
        "challenge.private_models.sha256": json.dumps({item["variant"]: item["sha256"] for item in models}, sort_keys=True),
        "challenge.final_linux_docker_load_verified": "false",
        "challenge.final_model_inference_verified": "false"})
    return config


def write_final_archive(stage_archive, partial_path, model_layer, final_config, image_tag,
                        layers, layer_expected):
    config_bytes = json_bytes(final_config)
    image_id = hashlib.sha256(config_bytes).hexdigest()
    new_layer_path = final_config["rootfs"]["diff_ids"][-1][7:] + "/layer.tar"
    config_path = image_id + ".json"
    require(new_layer_path not in layers and config_path not in layers, "New layer/config path collision")
    manifest = [{"Config": config_path, "RepoTags": [image_tag], "Layers": layers + [new_layer_path]}]
    seen, records = set(), []
    paths = set(layers) | {new_layer_path}
    directories = {str(parent) for path in paths for parent in PurePosixPath(path).parents if str(parent) != "."}
    with partial_path.open("xb") as raw:
        written = DigestWriter(raw)
        with tarfile.open(fileobj=written, mode="w|", format=tarfile.PAX_FORMAT) as output:
            for directory in sorted(directories, key=lambda value: (value.count("/"), value)):
                output.addfile(tar_info(directory, directory=True))
            with tarfile.open(stage_archive, "r|gz") as stage:
                for member in stage:
                    name = safe_archive_path(member.name, member.isdir())
                    if name not in layer_expected:
                        continue
                    require(name not in seen and member.isfile(), f"Duplicate/invalid layer on copy: {name}")
                    seen.add(name)
                    source = stage.extractfile(member)
                    require(source is not None, f"Cannot read old layer: {name}")
                    hashed = LayerReader(source)
                    output.addfile(tar_info(name, member.size), hashed)
                    digest = hashed.finish()
                    require(hashed.count == member.size and digest == layer_expected[name],
                            f"Actual uncompressed filesystem layer digest mismatch: {name}")
                    records.append({"archive_path": name, "stored_bytes": hashed.count,
                                    "stored_sha256": hashed.sha.hexdigest(), "diff_id": digest,
                                    "compression": hashed.compression})
                    print(f"Copied and verified stage layer {len(seen)}/{len(layer_expected)}", flush=True)
            require(seen == set(layer_expected), "Not all existing image layers were copied")
            with model_layer.open("rb") as source:
                hashed = DigestReader(source)
                output.addfile(tar_info(new_layer_path, model_layer.stat().st_size), hashed)
                require("sha256:" + hashed.sha.hexdigest() == final_config["rootfs"]["diff_ids"][-1],
                        "Private model layer changed while copying")
            output.addfile(tar_info(config_path, len(config_bytes)), io.BytesIO(config_bytes))
            manifest_bytes = json_bytes(manifest)
            output.addfile(tar_info("manifest.json", len(manifest_bytes)), io.BytesIO(manifest_bytes))
        written.flush()
        os.fsync(raw.fileno())
        final_sha, final_bytes = written.sha.hexdigest(), written.count
    return "sha256:" + image_id, final_sha, final_bytes, new_layer_path, records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-archive", type=Path, required=True)
    parser.add_argument("--stage-manifest", type=Path, required=True,
                        help="Actual downloaded stage_image_manifest.json; sidecars must be in the same directory")
    parser.add_argument("--expected-source-commit", required=True)
    parser.add_argument("--package-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="New directory within PACKAGE/02_源码与部署/docker/exports")
    parser.add_argument("--image-tag", default="challenge-student-x86:20261009")
    args = parser.parse_args()
    require(TAG.fullmatch(args.image_tag) is not None, "Use an explicit local repository:tag image name")
    archive = args.runtime_archive.resolve(strict=True)
    require(archive.is_file() and not args.runtime_archive.is_symlink(), "Stage archive is not a regular file")
    package = args.package_root.resolve(strict=True)
    require(package.is_dir(), "Package root does not exist")
    output = args.output_dir.resolve()
    export_root = (package / "02_源码与部署/docker/exports").resolve()
    require(export_root.is_relative_to(package) and output.is_relative_to(export_root) and output != export_root,
            "Output must be a child directory within the package Docker exports folder")
    target = output / "student-x86-image.tar"
    partial = output / "student-x86-image.tar.partial"
    temporary_layer = output / "private-model-layer.tmp"
    for path in (target, partial, temporary_layer, output / "assembly_manifest.json", output / "SHA256SUMS.txt"):
        require(not path.exists(), f"Refusing to overwrite existing export: {path}")
    print("Verifying the three real local formal model files...", flush=True)
    models = verify_models(package)
    metadata, config, layers, members, layer_expected = verify_stage(
        archive, args.stage_manifest.resolve(strict=True), args.expected_source_commit)
    created = utc_now()
    output.mkdir(parents=True, exist_ok=True)
    try:
        new_diff_id = build_model_layer(temporary_layer, models)
        predicted_bytes = sum(members[path]["size"] for path in set(layers)) + temporary_layer.stat().st_size + 16 * CHUNK
        free_bytes = shutil.disk_usage(output).free
        require(free_bytes >= predicted_bytes,
                f"Insufficient space: export needs approximately {predicted_bytes} bytes, free {free_bytes}")
        final_config = make_final_config(config, metadata, models, new_diff_id, created)
        image_id, digest, byte_count, new_layer_path, copied_layers = write_final_archive(
            archive, partial, temporary_layer, final_config, args.image_tag, layers, layer_expected)
        require(not target.exists(), "Final target appeared during assembly; refusing overwrite")
        partial.rename(target)
        manifest = {"status": "IMAGE_ARCHIVE_ASSEMBLED_PRIVATE_MODELS_ATTACHED_LINUX_LOAD_PENDING",
            "generated_at_utc": created, "archive_file": target.name, "archive_bytes": byte_count,
            "archive_sha256": digest, "image_tag": args.image_tag, "image_id_computed_from_config": image_id,
            "platform": "linux/amd64", "runtime_stage_image_id_observed": metadata["image_id"],
            "runtime_stage_source_commit": metadata["source_commit"], "runtime_stage_archive_sha256": metadata["archive_sha256"],
            "runtime_stage_run_url": metadata.get("run_url"), "resolved_base": metadata.get("resolved_base"),
            "base_kind": metadata["base_kind"],
            "official_environment_equivalent": metadata["official_environment_equivalent"],
            "official_base_ref": metadata.get("official_base_ref"),
            "official_base_access": metadata.get("official_base_access"),
            "private_model_files_included": True, "private_models_published": False,
            "runtime_stage_dependency_check_run": True, "runtime_stage_import_check_run": True,
            "final_image_linux_docker_load_run": False, "final_image_docker_inspect_run": False,
            "final_image_model_inference_run": False, "formal_A3_FP32_GATE_passed": False,
            "final_submission_zip_generated": False, "assembly_method": "Append one verified local model layer; preserve original stage layer bytes; emit manifest.json Docker archive",
            "rootfs_diff_ids": final_config["rootfs"]["diff_ids"], "original_layers": copied_layers,
            "new_model_layer_archive_path": new_layer_path, "new_model_layer_diff_id": new_diff_id,
            "models": [{key: value for key, value in model.items() if key != "source_path"} for model in models],
            "pending_validation": ["Linux docker load of the final archive", "Actual three-model ONNX load/inference and default HTTP service startup"],
            "downloaded_sidecar_sha256": {name: file_sha(args.stage_manifest.parent / name) for name in
                ("stage_image_manifest.json", "image_inspect.json", "runtime_dependencies.json", "build_status.json", "public_context_check.json", "registry_metadata.json", "base_image_inspect.json")}}
        (output / "assembly_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (output / "SHA256SUMS.txt").write_text(digest + "  " + target.name + "\n", encoding="ascii")
        print(json.dumps({"archive": str(target), "image_id_computed_from_config": image_id,
                          "archive_sha256": digest, "final_linux_load_verified": False,
                          "final_model_inference_verified": False}, ensure_ascii=False, indent=2))
    except Exception:
        # Only remove this invocation's incomplete output; never delete user data.
        if partial.is_file():
            partial.unlink()
        raise
    finally:
        if temporary_layer.is_file():
            temporary_layer.unlink()


if __name__ == "__main__":
    main()
