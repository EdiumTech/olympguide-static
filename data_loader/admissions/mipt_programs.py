"""Build the MIPT program directory from the saved official 2026 places table.

Run after: python -m admissions.sources mipt_places https://pk.mipt.ru/bachelor/2026_places/ mipt
No seat counts are assigned to individual programs: the source shares them among
competition groups, and repeated rows can describe targeted-training customers.
"""
import hashlib
import json
import re
from .paths import SNAPSHOT

SCHOOL_SCOPES = {
    "ВШМ": "ВШМ", "ФПМИ": "ФПМИ", "ФРКТ": "ФРКТ", "ЛФИ": "ЛФИ",
    "ФАКТ": "ФАКТ", "ПИШ ФАЛТ": "ПИШ ФАЛТ", "ФЭФМ": "ФЭФМ",
    "ФБМФ, ВШБИ": "ФБМФ/ ВШБИ", "КНТ": "КНТ", "ВШПИ": "ВШПИ", "ФБВТ": "ФБВТ",
}


def expand(rows):
    cells = {}
    width = 0
    for y, row in enumerate(rows):
        x = 0
        for cell in row:
            while (y, x) in cells:
                x += 1
            for dy in range(cell["rowspan"]):
                for dx in range(cell["colspan"]):
                    if (y + dy, x + dx) in cells:
                        raise ValueError("Overlapping source table cells")
                    cells[y + dy, x + dx] = cell["text"].strip()
            x += cell["colspan"]
            width = max(width, x)
    return [[cells.get((y, x), "") for x in range(width)] for y in range(len(rows))]


def parse(source):
    programs = {}
    field_code = field_name = None
    for row_number, row in enumerate(expand(source["tables"][0]), 1):
        heading = re.fullmatch(r"(\d{2}\.\d{2}\.\d{2})\s+(.+)", row[0])
        if heading:
            field_code, field_name = heading.groups()
            continue
        if row[0] not in SCHOOL_SCOPES:
            continue
        school, name, competition_group = row[:3]
        if not field_code or not name or not competition_group:
            raise ValueError(f"Incomplete program row {row_number}")
        key = hashlib.sha256("|".join(("mipt", field_code, school, name, competition_group)).encode()).hexdigest()[:20]
        item = programs.setdefault(key, {
            "id": key, "university_id": "mipt", "admission_year": 2026,
            "name": name, "field_id": field_code, "field_name": field_name,
            "school": school, "competition_group": competition_group,
            "rule_scope": SCHOOL_SCOPES[school], "kind": "program",
            "education_level": "Базовое высшее образование",
            "source_id": source["id"], "source_url": source["url"],
            "source_rows": [], "rule_relation": "school_conditions",
        })
        item["source_rows"].append(row_number)
    if len({p["field_id"] for p in programs.values()}) != 10:
        raise ValueError("Expected 10 directions in the official 2026 table; review source changes")
    if {p["school"] for p in programs.values()} != set(SCHOOL_SCOPES):
        raise ValueError("Not all schools from the 2026 table were parsed")
    return list(programs.values())


def build(snapshot=SNAPSHOT):
    source = json.loads((snapshot / "sources/mipt_places.json").read_text(encoding="utf-8"))
    data = {
        "schema_version": 1, "admission_year": 2026,
        "sources": [{k: v for k, v in source.items() if k not in ("text", "tables", "pages", "links")}],
        "programs": parse(source),
    }
    (snapshot / "programs.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return data


if __name__ == "__main__":
    data = build()
    print(f"MIPT: {len(data['programs'])} programs, 10 directions")
