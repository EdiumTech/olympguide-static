"""Pinned RSOSH academic-season catalogue; independent of university admission rules.

The 2026/2027 source is a draft, not an approved list. Original DOCX and
normalized JSON are distributed together in a checksummed Release archive.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import urllib.request
from xml.etree import ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED

from .download import install, read_manifest, verify_snapshot

ROOT = Path(__file__).resolve().parent
SEASON = "2026/2027"
STATUS = "draft"
PROJECT = "https://regulation.gov.ru/projects/170112/"
DOCUMENT = "https://regulation.gov.ru/api/public/Files/GetFile/66f40663-55eb-4174-8e71-5080ca3d5df7"
ANNOUNCEMENT = "https://rsr-olymp.ru/news/123"
CHECKED_ON = "2026-09-08"
SNAPSHOT = ROOT / "snapshots/rsosh-2026-2027"
MANIFEST = ROOT / "releases/rsosh-2026-2027.json"
TAG = "rsosh-2026-2027-draft-20260908"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

# Admissions-office addresses checked on official university pages. Scope is
# the main campus/undergraduate intake, never a department or branch address.
CONTACTS = [
    ("hse", "abitur@hse.ru", "https://ba.hse.ru/mirror/pubs/share/1146737784.pdf"),
    ("itmo", "abit@itmo.ru", "https://abit.itmo.ru/contacts"),
    ("bmstu", "abiturient@bmstu.ru", "https://mil.bmstu.ru/nabor_zapas"),
    ("mipt", "pk.bachelor@mipt.ru", "https://pk.mipt.ru/bachelor/"),
    ("mephi", "priem@mephi.ru", "https://admission.mephi.ru/information"),
    ("mai", "priem@mai.ru", "https://priem.mai.ru/contacts/"),
    ("msal", "priem@msal.ru", "https://msal.ru/"),
]


def normalized(text):
    return " ".join(text.replace("\xa0", " ").split())


def entry_key(name, profile):
    # Names/profile, not row numbers or levels: renumbering and a changed level
    # keep personal favourites. A genuinely renamed profile needs explicit review.
    text = "|".join(normalized(x).casefold().replace("ё", "е") for x in (name, profile))
    return "rsosh:" + SEASON + ":" + hashlib.sha256(text.encode()).hexdigest()[:24]


def parse_docx(path):
    with ZipFile(path) as doc:
        info = doc.getinfo("word/document.xml")
        if info.file_size > 20_000_000:
            raise ValueError("Unexpected document size")
        root = ET.fromstring(doc.read(info))
    text = "".join(t.text or "" for t in root.iter(W + "t"))
    if "2026/27" not in text or "2026 г № ____" not in text:
        raise ValueError("Expected the reviewed 2026/27 draft")
    rows = root.findall(".//" + W + "tr")
    result, ordinal, name = [], None, None
    for index, row in enumerate(rows[2:], 3):
        cells = row.findall(W + "tc")
        values = [normalized("".join(t.text or "" for t in c.iter(W + "t"))) for c in cells]
        if len(values) != 6:
            raise ValueError(f"Unexpected columns in source row {index}")
        number, title, organizers, profile, subjects, level = values
        if number:
            ordinal = int(number.replace(" ", ""))
            name = title
        elif title or cells[0].find(".//" + W + "vMerge") is None:
            raise ValueError(f"Unverified continuation row {index}")
        if not name or not profile or not subjects or level not in ("I", "II", "III"):
            raise ValueError(f"Missing profile/subject/level in row {index}")
        result.append(dict(id=entry_key(name, profile), registry_number=ordinal, name=name,
                           profile=profile, subjects=subjects, level=len(level),
                           organizers=organizers, source_row=index, category="rsosh",
                           academic_year=SEASON, registry_status=STATUS, source_url=PROJECT))
    return result


def validate(data):
    if (data.get("schema_version"), data.get("academic_year"), data.get("status")) != (1, SEASON, STATUS):
        raise ValueError("Unexpected registry season or publication status")
    if data.get("source_url") != PROJECT or data.get("document_url") != DOCUMENT:
        raise ValueError("Unreviewed registry source")
    entries = data["olympiads"]
    if len({e["id"] for e in entries}) != len(entries):
        raise ValueError("Duplicate olympiad/profile identity")
    if {e["registry_number"] for e in entries} != set(range(1, 80)):
        raise ValueError("Expected all 79 olympiads")
    if len(entries) != 303:
        raise ValueError("Expected all 303 profile rows from the reviewed draft")
    for e in entries:
        if (e["category"] != "rsosh" or e["academic_year"] != SEASON or e["registry_status"] != STATUS
                or type(e["level"]) is not int or e["level"] not in (1, 2, 3)
                or not e["profile"].strip() or not e["subjects"].strip()
                or e["id"] != entry_key(e["name"], e["profile"]) or e["source_url"] != PROJECT):
            raise ValueError("Invalid registry entry")
    contacts = data["contacts"]
    if {(c["university_key"], c["email"], c["source_url"]) for c in contacts} != set(CONTACTS):
        raise ValueError("Unreviewed contact data")
    return dict(olympiads=79, profiles=len(entries), academic_year=SEASON, status=STATUS)


def load(target=SNAPSHOT, manifest_path=MANIFEST):
    target = Path(target)
    manifest = read_manifest(manifest_path)
    verify_snapshot(target, manifest)
    data = json.loads((target / "catalog.json").read_text(encoding="utf-8"))
    validate(data)
    if data["olympiads"] != parse_docx(target / "sources/project.docx"):
        raise ValueError("Normalized registry differs from its official document")
    return data


def build(target=SNAPSHOT):
    target = Path(target)
    (target / "sources").mkdir(parents=True, exist_ok=True)
    document = target / "sources/project.docx"
    if not document.exists():
        with urllib.request.urlopen(DOCUMENT, timeout=40) as response:
            document.write_bytes(response.read(5_000_001))
        if document.stat().st_size > 5_000_000:
            raise ValueError("Unexpected source size")
    data = dict(schema_version=1, academic_year=SEASON, status=STATUS, checked_on=CHECKED_ON,
                source_url=PROJECT, document_url=DOCUMENT, announcement_url=ANNOUNCEMENT,
                olympiads=parse_docx(document), contacts=[dict(university_key=key, email=email,
                source_url=url, checked_on=CHECKED_ON, scope="Приёмная комиссия основного кампуса, бакалавриат / специалитет")
                for key, email, url in CONTACTS])
    validate(data)
    (target / "catalog.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return data


def package(target=SNAPSHOT):
    target = Path(target)
    data = json.loads((target / "catalog.json").read_text(encoding="utf-8"))
    validate(data)
    archive = target.parent / (TAG + ".zip")
    files = ["catalog.json", "sources/project.docx"]
    def facts(path):
        return dict(bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    with ZipFile(archive, "w", ZIP_DEFLATED) as bundle:
        for name in files:
            bundle.write(target / name, name)
    manifest = dict(schema_version=1, kind="rsosh", academic_year=SEASON, status=STATUS,
                    checked_on=CHECKED_ON, release_tag=TAG,
                    archive=dict(url=f"https://github.com/EdiumTech/olympguide-static/releases/download/{TAG}/{archive.name}", **facts(archive)),
                    files=[dict(path=name, **facts(target / name)) for name in files])
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return archive


def literal(value):
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if "\x00" in str(value):
        raise ValueError("NUL in registry data")
    return "'" + str(value).replace("'", "''") + "'"


def calendar_registry_sql():
    # This collection is the verified 2026/27 Higher Test calendar. Link new
    # identities only to that same season; this never creates admission rules.
    return """UPDATE olympguide.calendar_event e SET payload=payload || jsonb_build_object(
      'olympiad_keys',(SELECT jsonb_agg(DISTINCT k) FROM (
        SELECT jsonb_array_elements_text(COALESCE(e.payload->'olympiad_keys','[]')) k
        UNION SELECT catalog_key FROM olympguide.olympiad WHERE registry_active AND academic_year='2026/2027'
          AND name='Всероссийская олимпиада школьников «Высшая проба»') keys),
      'olympiad_ids',(SELECT jsonb_agg(DISTINCT n) FROM (
        SELECT jsonb_array_elements(COALESCE(e.payload->'olympiad_ids','[]')) n
        UNION SELECT to_jsonb(olympiad_id) FROM olympguide.olympiad WHERE registry_active AND academic_year='2026/2027'
          AND name='Всероссийская олимпиада школьников «Высшая проба»') ids)
      ) WHERE collection_key='hse-vp-2026-2027' AND season='2026/2027';"""


def export_sql(data):
    validate(data)
    season = literal(SEASON)
    sql = ["BEGIN;", "SET LOCAL standard_conforming_strings=on;", "SET LOCAL lock_timeout='15s';",
           "SELECT pg_advisory_xact_lock(2026, 7891);",
           "INSERT INTO olympguide.olympiad_registry_release(academic_year,status,payload) VALUES (" +
           season + "," + literal(STATUS) + "," + literal({k:v for k,v in data.items() if k not in ('olympiads','contacts')}) +
           ") ON CONFLICT(academic_year) DO UPDATE SET status=EXCLUDED.status,payload=EXCLUDED.payload,imported_at=now();",
           f"UPDATE olympguide.olympiad SET registry_active=false WHERE academic_year={season};"]
    for e in data["olympiads"]:
        description = "Проект перечня РСОШ 2026/2027. Условия поступления по этому сезону пока не подтверждены."
        values = [e['id'], e['name'], e['profile'], e['subjects'], e['level'], 'rsosh', SEASON, STATUS, PROJECT, description]
        sql.append("INSERT INTO olympguide.olympiad(catalog_key,name,profile,subjects,level,category,academic_year,registry_status,link,description,registry_active) VALUES (" +
                   ",".join(literal(v) for v in values) + ",true) ON CONFLICT(catalog_key) DO UPDATE SET " +
                   ",".join(f"{k}=EXCLUDED.{k}" for k in ('name','profile','subjects','level','category','academic_year','registry_status','link','description','registry_active')) + ";")
    for c in data['contacts']:
        sql.append("UPDATE olympguide.university SET email=" + literal(c['email']) + ",contact_metadata=" + literal(c) +
                   "::jsonb WHERE catalog_key=" + literal(c['university_key']) + ";")
    sql += [calendar_registry_sql(), "COMMIT;"]
    return "\n".join(sql) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "package", "download", "validate", "export-sql"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.command == "build": print(validate(build()))
    elif args.command == "package": print(package())
    elif args.command == "download": print(install(manifest_path=MANIFEST, target=SNAPSHOT))
    elif args.command == "validate": print(validate(load()))
    else:
        if not args.output: parser.error("export-sql requires --output")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(export_sql(load()), encoding="utf-8")


if __name__ == "__main__":
    main()
