#!/usr/bin/env python3
"""Verify OnlyShell's final release files. No network access or publication."""
import argparse
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

VARIANTS = {
    "self-contained": ("SelfContained", "OnlyShellSelfContained"),
    "framework-dependent": ("FrameworkDependent", "OnlyShellFrameworkDependent"),
}
SEMVER = re.compile(r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)")


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def names(version, variant):
    if not SEMVER.fullmatch(version) or variant not in VARIANTS:
        raise ValueError("Expected stable SemVer and a known variant")
    display, package_id = VARIANTS[variant]
    channel = f"win-x64-{variant}"
    required = {
        f"OnlyShell-{display}-v{version}-win-x64-Setup.exe",
        f"{package_id}-{channel}-Setup.exe",
        f"{package_id}-{channel}-Portable.zip",
        f"{package_id}-{version}-{channel}-full.nupkg",
        f"releases.{channel}.json",
    }
    return package_id, channel, required, f"{package_id}-{version}-{channel}-delta.nupkg"


def verify_payload(directory, version, variant):
    package_id, channel, required, delta = names(version, variant)
    entries = list(directory.iterdir())
    if any(p.is_symlink() or not p.is_file() for p in entries):
        raise ValueError("Assets must be regular files, without directories or symbolic links")
    actual = {p.name for p in entries} - {"SHA256SUMS.txt", "RELEASE-MANIFEST.json"}
    if not required <= actual or actual - required - {delta}:
        raise ValueError(f"Unexpected asset set: missing={required-actual}, extra={actual-required-{delta}}")
    if any((directory / name).stat().st_size == 0 for name in actual):
        raise ValueError("Empty release asset")
    feed = json.loads((directory / f"releases.{channel}.json").read_text(encoding="utf-8-sig"))
    assets = feed["Assets"]
    expected_packages = {name for name in actual if name.endswith(".nupkg")}
    if len(assets) != len(expected_packages) or {a["FileName"] for a in assets} != expected_packages:
        raise ValueError("Feed must contain exactly this release's uploaded packages")
    for asset in assets:
        path = directory / asset["FileName"]
        expected_type = "Full" if path.name.endswith("-full.nupkg") else "Delta"
        if (asset["Version"] != version or asset["PackageId"] != package_id
                or asset["Type"] != expected_type or asset["Size"] != path.stat().st_size
                or asset["SHA256"].lower() != digest(path)):
            raise ValueError("Feed version, identity, type, size or SHA256 mismatch")
    full = directory / f"{package_id}-{version}-{channel}-full.nupkg"
    with zipfile.ZipFile(full) as archive:
        specs = [name for name in archive.namelist() if name.endswith(".nuspec")]
        if len(specs) != 1 or "lib/app/OnlyShell.exe" not in archive.namelist():
            raise ValueError("Full package lacks the expected application or unique nuspec")
        root = ET.fromstring(archive.read(specs[0]))
        metadata = {node.tag.rsplit("}", 1)[-1]: node.text for node in root.iter()}
        if metadata.get("id") != package_id or metadata.get("version") != version:
            raise ValueError("Full package identity/version mismatch")
    with zipfile.ZipFile(directory / f"{package_id}-{channel}-Portable.zip") as archive:
        if "OnlyShell.exe" not in archive.namelist():
            raise ValueError("Portable ZIP lacks OnlyShell.exe")
    return actual


def write_manifest(directory, version, variant, source):
    if not re.fullmatch(r"[0-9a-f]{40}", source):
        raise ValueError("An exact source commit SHA is required")
    if (directory / "SHA256SUMS.txt").exists() or (directory / "RELEASE-MANIFEST.json").exists():
        raise ValueError("Refusing to overwrite an existing manifest")
    assets = verify_payload(directory, version, variant)
    package_id, channel, _, _ = names(version, variant)
    manifest = {
        "version": version, "tag": f"v{version}-{variant}", "sourceCommit": source,
        "packageId": package_id, "channel": channel, "runtime": "win-x64",
        "assets": [{"name": name, "size": (directory / name).stat().st_size,
                    "sha256": digest(directory / name)} for name in sorted(assets)],
    }
    (directory / "RELEASE-MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    assets.add("RELEASE-MANIFEST.json")
    (directory / "SHA256SUMS.txt").write_text(
        "".join(f"{digest(directory / name)}  {name}\n" for name in sorted(assets)), encoding="utf-8")


def verify(directory, version, variant, source):
    actual = verify_payload(directory, version, variant)
    manifest = json.loads((directory / "RELEASE-MANIFEST.json").read_text(encoding="utf-8"))
    package_id, channel, _, _ = names(version, variant)
    if (manifest["version"] != version or manifest["tag"] != f"v{version}-{variant}"
            or manifest["sourceCommit"] != source or not re.fullmatch(r"[0-9a-f]{40}", source)
            or manifest["packageId"] != package_id or manifest["channel"] != channel
            or manifest["runtime"] != "win-x64"):
        raise ValueError("Release metadata does not match the approved source/version/channel")
    expected = {a["name"]: a for a in manifest["assets"]}
    if len(expected) != len(manifest["assets"]) or set(expected) != actual:
        raise ValueError("Manifest asset set mismatch")
    for name, asset in expected.items():
        if asset["sha256"] != digest(directory / name) or asset["size"] != (directory / name).stat().st_size:
            raise ValueError(f"Manifest hash/size mismatch: {name}")
    checksum_lines = (directory / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines()
    sums = {}
    for line in checksum_lines:
        match = re.fullmatch(r"([0-9a-f]{64})  ([^/\\]+)", line)
        if not match or match[2] in sums:
            raise ValueError("Malformed/duplicate checksum entry")
        sums[match[2]] = match[1]
    if set(sums) != actual | {"RELEASE-MANIFEST.json"}:
        raise ValueError("Checksum asset set mismatch")
    if any(digest(directory / name) != value for name, value in sums.items()):
        raise ValueError("SHA256SUMS mismatch")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--variant", choices=VARIANTS, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--write-manifest", action="store_true")
    args = parser.parse_args()
    try:
        if args.write_manifest:
            write_manifest(args.directory, args.version, args.variant, args.source_sha)
        verify(args.directory, args.version, args.variant, args.source_sha)
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile, ET.ParseError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"Release assets verified: {args.version} / {args.variant} / {args.source_sha}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
