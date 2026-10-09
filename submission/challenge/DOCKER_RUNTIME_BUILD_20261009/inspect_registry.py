#!/usr/bin/env python3
"""Read anonymous registry metadata and stop before oversized Docker downloads."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import urllib.parse
import urllib.request

REPOSITORY = "openexplorer/ai_toolchain_ubuntu_22_j6_cpu"
TAG = "v3.9.1"
GIB = 1024 ** 3
ACCEPT = ",".join((
    "application/vnd.oci.image.index.v1+json",
    "application/vnd.docker.distribution.manifest.list.v2+json",
    "application/vnd.docker.distribution.manifest.v2+json",
    "application/vnd.oci.image.manifest.v1+json",
))


def read_json(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=45) as response:
        body = response.read(8 * 1024 * 1024 + 1)
        if len(body) > 8 * 1024 * 1024:
            raise RuntimeError("Registry metadata exceeded 8 MiB; no layer was downloaded")
        digest = response.headers.get("Docker-Content-Digest")
        if digest and digest != "sha256:" + hashlib.sha256(body).hexdigest():
            raise RuntimeError("Registry manifest body does not match its content digest")
        return json.loads(body), digest or "sha256:" + hashlib.sha256(body).hexdigest()


def write_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-compressed-bytes", type=int, default=10 * GIB)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    metadata = {
        "status": "PREFLIGHT_STARTED", "base_tag": REPOSITORY + ":" + TAG,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "source_commit": os.environ.get("GITHUB_SHA"),
        "registry_authentication": "ANONYMOUS_PULL_TOKEN_NO_CUSTOM_SECRET",
        "private_model_files_included": False, "final_student_image_built": False,
    }
    try:
        query = urllib.parse.urlencode({
            "service": "registry.docker.io", "scope": "repository:" + REPOSITORY + ":pull",
        })
        auth, _ = read_json("https://auth.docker.io/token?" + query)
        # Do not log this transient anonymous bearer token or store it in artifacts.
        headers = {"Authorization": "Bearer " + auth["token"], "Accept": ACCEPT}
        endpoint = "https://registry-1.docker.io/v2/" + REPOSITORY + "/manifests/"
        manifest, tag_digest = read_json(endpoint + TAG, headers)
        write_json(args.output / "registry_tag_manifest.json", manifest)
        selected_digest = tag_digest
        if "manifests" in manifest:
            matches = [row for row in manifest["manifests"]
                       if row.get("platform", {}).get("os") == "linux"
                       and row.get("platform", {}).get("architecture") == "amd64"]
            if len(matches) != 1:
                raise RuntimeError("Expected exactly one Linux amd64 manifest")
            selected_digest = matches[0]["digest"]
            manifest, actual_digest = read_json(endpoint + selected_digest, headers)
            if actual_digest != selected_digest:
                raise RuntimeError("Selected Linux amd64 manifest digest changed")
        layers = manifest.get("layers")
        if not isinstance(layers, list) or not layers:
            raise RuntimeError("Registry response is not a nonempty image manifest")
        compressed = sum(int(layer["size"]) for layer in layers)
        free_output = shutil.disk_usage(args.output).free
        free_docker = shutil.disk_usage("/var/lib/docker").free
        # A documented conservative capacity guard, not a measured expanded size.
        conservative_required = 3 * compressed + 6 * GIB
        metadata.update({
            "tag_manifest_digest": tag_digest,
            "selected_platform_manifest_digest": selected_digest,
            "resolved_base": REPOSITORY + "@" + selected_digest,
            "compressed_layers_bytes": compressed, "layer_count": len(layers),
            "runner_output_free_bytes": free_output,
            "runner_docker_free_bytes": free_docker,
            "conservative_minimum_free_bytes": conservative_required,
            "capacity_formula": "3 * compressed_layers_bytes + 6 GiB; conservative guard, not measured expansion",
            "max_compressed_bytes": args.max_compressed_bytes,
        })
        write_json(args.output / "registry_platform_manifest.json", manifest)
        if compressed > args.max_compressed_bytes:
            raise RuntimeError("Official compressed layers exceed configured download limit")
        if min(free_output, free_docker) < conservative_required:
            raise RuntimeError("Runner has insufficient free disk for the conservative pull/build/export guard")
        metadata["status"] = "PREFLIGHT_PASSED_NO_IMAGE_LAYERS_DOWNLOADED"
        env_path = os.environ.get("GITHUB_ENV")
        if env_path:
            with open(env_path, "a", encoding="utf-8") as stream:
                stream.write("RESOLVED_BASE=" + metadata["resolved_base"] + "\n")
        print(json.dumps(metadata, ensure_ascii=False, indent=2))
    except Exception as exc:
        metadata.update(status="PREFLIGHT_FAILED", error=type(exc).__name__ + ": " + str(exc))
        raise
    finally:
        write_json(args.output / "registry_metadata.json", metadata)


if __name__ == "__main__":
    main()
