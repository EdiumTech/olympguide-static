"""Download a pinned release snapshot and verify every file before installing it."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
import tempfile
import urllib.request
import zipfile

from .paths import ROOT, SNAPSHOT

MANIFEST = ROOT / "releases/2026.json"


def read_manifest(path=MANIFEST):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or data.get("admission_year") != 2026:
        raise ValueError("Unsupported release manifest")
    files = data["files"]
    if not files:
        raise ValueError("Empty snapshot manifest")
    names = set()
    for item in files:
        name = item["path"]
        parts = PurePosixPath(name).parts
        if (not parts or name.startswith("/") or "\\" in name or ":" in name
                or any(not p or p in (".", "..") or p.rstrip(" .") != p for p in name.split("/"))
                or name.casefold() in names):
            raise ValueError("Invalid or duplicate snapshot path")
        names.add(name.casefold())
    for item in [data["archive"], *files]:
        if (not isinstance(item["bytes"], int) or item["bytes"] < 0
                or not re.fullmatch(r"[0-9a-f]{64}", item["sha256"])):
            raise ValueError("Invalid size or checksum in manifest")
    return data


def check_file(path, item):
    if path.is_symlink() or not path.is_file() or path.stat().st_size != item["bytes"]:
        raise ValueError(f"Missing file or size mismatch: {path.name}")
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != item["sha256"]:
        raise ValueError(f"Checksum mismatch: {path.name}")


def verify_snapshot(target, manifest):
    root = Path(target).resolve()
    for item in manifest["files"]:
        path = root / item["path"]
        if not path.resolve().is_relative_to(root):
            raise ValueError("Snapshot path escapes its directory")
        check_file(path, item)


def install(*, manifest_path=MANIFEST, target=SNAPSHOT, archive=None):
    manifest = read_manifest(manifest_path)
    target = Path(target).resolve()
    if target.exists():
        # Never replace a user's rebuilt or updated local dataset.
        verify_snapshot(target, manifest)
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".admissions-", dir=target.parent) as temporary:
        temporary = Path(temporary).resolve()
        if temporary.parent != target.parent:
            raise ValueError("Unexpected staging directory")
        archive_path = Path(archive) if archive is not None else temporary / "snapshot.zip"
        if archive is None:
            url = manifest["archive"]["url"]
            if not url.startswith("https://github.com/"):
                raise ValueError("Expected an HTTPS GitHub Release URL")
            request = urllib.request.Request(url, headers={"User-Agent": "OlympGuide/1.0"})
            with urllib.request.urlopen(request, timeout=60) as response, archive_path.open("wb") as output:
                size = 0
                while chunk := response.read(1024 * 1024):
                    size += len(chunk)
                    if size > manifest["archive"]["bytes"]:
                        raise ValueError("Download exceeds the manifest size")
                    output.write(chunk)
        check_file(archive_path, manifest["archive"])
        expected = {item["path"]: item for item in manifest["files"]}
        staged = temporary / "snapshot"
        staged.mkdir()
        with zipfile.ZipFile(archive_path) as bundle:
            members = bundle.infolist()
            if len(members) != len(expected) or {m.filename for m in members} != set(expected):
                raise ValueError("Archive contents differ from the manifest")
            for member in members:
                item = expected[member.filename]
                if (member.is_dir() or stat.S_ISLNK(member.external_attr >> 16)
                        or member.file_size != item["bytes"]):
                    raise ValueError("Invalid snapshot archive entry")
                destination = staged / member.filename
                if not destination.resolve().is_relative_to(staged.resolve()):
                    raise ValueError("Archive path escapes staging directory")
                destination.parent.mkdir(parents=True, exist_ok=True)
                with bundle.open(member) as source, destination.open("wb") as output:
                    for chunk in iter(lambda: source.read(1024 * 1024), b""):
                        output.write(chunk)
                check_file(destination, item)
        staged.rename(target)
    return target
