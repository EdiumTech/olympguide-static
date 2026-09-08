"""Collect and normalize official university organization/program directories."""
import argparse
import hashlib
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from .paths import SNAPSHOT

ROOT = SNAPSHOT / "organization"


def fetch(key, university, url):
    if not re.fullmatch(r"[a-z0-9_]+", key):
        raise ValueError("Invalid source key")
    root = ROOT / "sources"
    root.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "OlympGuide/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        body, resolved, mime = response.read(), response.url, response.headers.get_content_type()
    suffix = ".pdf" if body.startswith(b"%PDF") else ".json" if mime == "application/json" else ".html"
    path = root / (key + suffix)
    path.write_bytes(body)
    metadata = dict(id=key, university=university, url=url, resolved_url=resolved,
                    retrieved_at=datetime.now(timezone.utc).isoformat(),
                    sha256=hashlib.sha256(body).hexdigest(), file=path.name)
    (root / (key + ".meta.json")).write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return metadata


def extract_pdf():
    """Save a checksum-bound table extraction; requires the collector packages."""
    import pdfplumber
    metadata = json.loads((ROOT / "sources/msal_tracks.meta.json").read_text(encoding="utf-8"))
    path = ROOT / "sources" / metadata["file"]
    with pdfplumber.open(path) as document:
        pages = [{"text": p.extract_text(), "tables": p.extract_tables()} for p in document.pages]
    result = {"source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "pages": pages}
    (ROOT / "sources/msal_tracks.extracted.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate():
    data = json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))
    if data["admission_year"] != 2026 or data["schema_version"] != 1:
        raise ValueError("Unexpected organization catalog version")
    sources = {s["id"]: s for s in data["sources"]}
    units = {u["id"]: u for u in data["units"]}
    if len(units) != len(data["units"]) or len({p["id"] for p in data["programs"]}) != len(data["programs"]):
        raise ValueError("Duplicate organization entity id")
    for source in sources.values():
        path = (SNAPSHOT / source["file"]).resolve()
        if not path.is_relative_to(ROOT.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest() != source["sha256"]:
            raise ValueError("Invalid organization source: " + source["id"])
    for unit in units.values():
        if unit["parent_id"] and (unit["parent_id"] not in units or units[unit["parent_id"]]["university_id"] != unit["university_id"]):
            raise ValueError("Invalid unit parent")
        if any(s not in sources for s in unit["source_ids"]):
            raise ValueError("Missing unit provenance")
    for p in data["programs"]:
        if not p["unit_ids"] or not re.fullmatch(r"\d{2}\.\d{2}\.\d{2}", p["field_id"]):
            raise ValueError("Missing program affiliation/field")
        for uid in p["unit_ids"] + p.get("department_ids", []):
            if uid not in units or units[uid]["university_id"] != p["university_id"]:
                raise ValueError("Invalid program unit")
        if any(a["source_id"] not in sources or not a["locator"] for a in p["affiliations"]):
            raise ValueError("Missing affiliation provenance")
    universities = {u["university_id"] for u in units.values()}
    if universities != {"hse", "itmo", "bmstu", "mipt", "mephi", "mai", "msal"}:
        raise ValueError("Incomplete university set")
    return {"universities": len(universities), "units": len(units), "programs": len(data["programs"])}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("key", nargs="?")
    parser.add_argument("university", nargs="?")
    parser.add_argument("url", nargs="?")
    parser.add_argument("--extract-pdf", action="store_true")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--refresh", action="store_true", help="Refetch the pinned URLs from organization/catalog.json")
    args = parser.parse_args()
    if args.extract_pdf:
        extract_pdf()
    elif args.validate:
        print(json.dumps(validate(), ensure_ascii=False))
    elif args.refresh:
        catalog = json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))
        for source in catalog["sources"]:
            print(fetch(source["id"], source["university"], source["url"])["id"], flush=True)
        extract_pdf()
    elif all((args.key, args.university, args.url)):
        print(json.dumps(fetch(args.key, args.university, args.url), ensure_ascii=False))
    else:
        parser.error("Specify key university url, --refresh, --extract-pdf or --validate")
