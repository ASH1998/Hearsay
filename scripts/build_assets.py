from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import unquote
from zipfile import ZipFile

REPO_ROOT = Path(__file__).resolve().parents[1]
SELECTION_PATH = REPO_ROOT / "assets" / "selection.json"
MANIFEST_PATH = REPO_ROOT / "assets" / "manifest.json"
REPORT_PATH = REPO_ROOT / "assets" / "VALIDATION_REPORT.md"
SOURCE_ROOT = REPO_ROOT / "assets" / "source"
PUBLIC_ROOT = REPO_ROOT / "apps" / "web" / "public"
GLTF_TRANSFORM = REPO_ROOT / "node_modules" / "@gltf-transform" / "cli" / "bin" / "cli.js"
INITIAL_BUDGET = 25 * 1024 * 1024
SESSION_BUDGET = 60 * 1024 * 1024
DRAW_CALL_BUDGET = 300


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_member(name: str) -> PurePosixPath:
    member = PurePosixPath(name)
    if member.is_absolute() or ".." in member.parts:
        raise ValueError(f"Unsafe archive member: {name}")
    return member


def extract_member(archive: ZipFile, name: str, destination: Path) -> Path:
    member = safe_member(name)
    info = archive.getinfo(member.as_posix())
    if info.file_size > 256 * 1024 * 1024:
        raise ValueError(f"Archive member is unexpectedly large: {name}")
    output = destination.joinpath(*member.parts)
    output.parent.mkdir(parents=True, exist_ok=True)
    with archive.open(info) as source, output.open("wb") as target:
        shutil.copyfileobj(source, target)
    return output


def gltf_dependencies(archive: ZipFile, entry: str) -> list[str]:
    if not entry.lower().endswith(".gltf"):
        return []
    document = json.loads(archive.read(entry))
    parent = safe_member(entry).parent
    dependencies: list[str] = []
    for section in ("buffers", "images"):
        for item in document.get(section, []):
            uri = item.get("uri")
            if not uri or uri.startswith("data:"):
                continue
            dependency = parent / safe_member(unquote(uri))
            dependencies.append(dependency.as_posix())
    return dependencies


def optimize_model(source: Path, output: Path, profile: str) -> None:
    if not GLTF_TRANSFORM.is_file():
        raise FileNotFoundError("glTF Transform is missing. Run the repository bootstrap first.")
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "node",
        str(GLTF_TRANSFORM),
        "optimize",
        str(source),
        str(output),
        "--compress",
        "quantize",
        "--simplify",
        "false",
        "--texture-compress",
        "webp",
        "--texture-size",
        "1024",
    ]
    if profile in {"character", "animation"}:
        command.extend(
            [
                "--flatten",
                "false",
                "--join",
                "false",
                "--instance",
                "false",
                "--palette",
                "false",
            ]
        )
    subprocess.run(command, cwd=REPO_ROOT, check=True)


def glb_metrics(path: Path) -> tuple[int, int, int]:
    with path.open("rb") as handle:
        header = handle.read(20)
        if len(header) < 20 or header[:4] != b"glTF":
            raise ValueError(f"Invalid GLB output: {path}")
        json_length, json_type = struct.unpack_from("<II", header, 12)
        if json_type != 0x4E4F534A:
            raise ValueError(f"GLB JSON chunk is missing: {path}")
        document = json.loads(handle.read(json_length))
    draw_calls = sum(len(mesh.get("primitives", [])) for mesh in document.get("meshes", []))
    triangles = 0
    accessors = document.get("accessors", [])
    for mesh in document.get("meshes", []):
        for primitive in mesh.get("primitives", []):
            if primitive.get("mode", 4) != 4:
                continue
            accessor_index = primitive.get("indices")
            if accessor_index is not None:
                triangles += accessors[accessor_index].get("count", 0) // 3
    return draw_calls, triangles, len(document.get("animations", []))


def build_asset(specification: dict[str, Any]) -> dict[str, Any]:
    archive_path = REPO_ROOT / specification["archive"]
    output_path = REPO_ROOT / specification["output"]
    if not archive_path.is_file():
        raise FileNotFoundError(f"Candidate archive is missing: {archive_path}")

    source_directory = SOURCE_ROOT / specification["id"]
    with ZipFile(archive_path) as archive:
        source = extract_member(archive, specification["entry"], source_directory)
        if specification["kind"] == "model":
            for dependency in gltf_dependencies(archive, specification["entry"]):
                extract_member(archive, dependency, source_directory)
            optimize_model(source, output_path, specification["profile"])
        else:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, output_path)

    result = dict(specification)
    result["archive_sha256"] = sha256(archive_path)
    result["bytes"] = output_path.stat().st_size
    result["sha256"] = sha256(output_path)
    if specification["kind"] == "model":
        draw_calls, triangles, animations = glb_metrics(output_path)
        result["draw_calls"] = draw_calls
        result["triangles"] = triangles
        result["animations"] = animations
    return result


def public_output(asset: dict[str, Any]) -> Path:
    return PUBLIC_ROOT / asset["runtime_path"].removeprefix("/")


def sync_public_assets(assets: list[dict[str, Any]]) -> None:
    for asset in assets:
        source = REPO_ROOT / asset["output"]
        destination = public_output(asset)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)


def validate_assets(assets: list[dict[str, Any]]) -> tuple[int, int, int]:
    initial_bytes = 0
    session_bytes = 0
    draw_calls = 0
    for asset in assets:
        output = REPO_ROOT / asset["output"]
        if not output.is_file():
            raise FileNotFoundError(f"Runtime asset is missing: {asset['output']}")
        actual_size = output.stat().st_size
        actual_hash = sha256(output)
        if actual_size != asset["bytes"] or actual_hash != asset["sha256"]:
            raise ValueError(f"Runtime asset checksum changed: {asset['id']}")
        session_bytes += actual_size
        draw_calls += asset.get("draw_calls", 0)
        if asset["initial_load"]:
            initial_bytes += actual_size
    if initial_bytes > INITIAL_BUDGET:
        raise ValueError("Initial runtime asset budget exceeded (25 MB).")
    if session_bytes > SESSION_BUDGET:
        raise ValueError("Full-session runtime asset budget exceeded (60 MB).")
    if draw_calls > DRAW_CALL_BUDGET:
        raise ValueError("Runtime draw-call budget exceeded (300).")
    return initial_bytes, session_bytes, draw_calls


def validate_public_assets(assets: list[dict[str, Any]]) -> None:
    for asset in assets:
        deployed = public_output(asset)
        if not deployed.is_file() or sha256(deployed) != asset["sha256"]:
            raise ValueError(f"Public asset is stale or missing: {asset['id']}")


def write_report(
    assets: list[dict[str, Any]],
    initial_bytes: int,
    session_bytes: int,
    draw_calls: int,
) -> None:
    lines = [
        "# Runtime asset validation",
        "",
        "Generated by `scripts/build_assets.py` from ignored candidate archives.",
        "",
        "| Asset | Kind | Creator | Initial | Bytes | Draw calls | SHA-256 |",
        "|---|---|---|---:|---:|---:|---|",
    ]
    for asset in assets:
        lines.append(
            f"| {asset['id']} | {asset['kind']} | {asset['creator']} | "
            f"{'yes' if asset['initial_load'] else 'no'} | {asset['bytes']:,} | "
            f"{asset.get('draw_calls', 0)} | `{asset['sha256']}` |"
        )
    lines.extend(
        [
            "",
            f"- Initial load: {initial_bytes / 1024 / 1024:.2f} MB / 25 MB.",
            f"- Full session: {session_bytes / 1024 / 1024:.2f} MB / 60 MB.",
            f"- Source draw calls: {draw_calls} / {DRAW_CALL_BUDGET}.",
            "- Every selected source is CC0 1.0; attribution is retained voluntarily.",
            "",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def archives_available(selection: dict[str, Any]) -> bool:
    return all((REPO_ROOT / asset["archive"]).is_file() for asset in selection["assets"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and validate Hearsay assets.")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    selection = json.loads(SELECTION_PATH.read_text(encoding="utf-8"))

    if not args.validate_only and archives_available(selection):
        assets = [build_asset(specification) for specification in selection["assets"]]
        manifest = {
            "schema_version": 1,
            "initial_load_budget_bytes": INITIAL_BUDGET,
            "full_session_budget_bytes": SESSION_BUDGET,
            "draw_call_budget": DRAW_CALL_BUDGET,
            "assets": assets,
            "candidate_archives": sorted({asset["archive"] for asset in selection["assets"]}),
        }
        MANIFEST_PATH.write_text(
            json.dumps(manifest, indent=2) + "\n",
            encoding="utf-8",
        )
    else:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        assets = manifest["assets"]

    initial_bytes, session_bytes, draw_calls = validate_assets(assets)
    sync_public_assets(assets)
    validate_public_assets(assets)
    write_report(assets, initial_bytes, session_bytes, draw_calls)
    print(
        f"Validated {len(assets)} runtime assets "
        f"({initial_bytes / 1024 / 1024:.2f} MB initial, "
        f"{session_bytes / 1024 / 1024:.2f} MB session, "
        f"{draw_calls} source draw calls)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
