"""Read-only web projections of the versioned admissions catalog.

An explicit list of field codes can be split into fields. Scopes with exceptions,
conditions or school names remain separate groups; they are never interpreted as
an unconditional offer for each code mentioned in the text.
"""
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_CATALOG = ROOT.parent / "data_loader/admissions/snapshots/2026/catalog.json"
CODE = re.compile(r"\d{2}\.\d{2}\.\d{2}")


def normalized(value):
    return " ".join(re.sub(r"[^\w]+", " ", value.casefold().replace("ё", "е")).split())


def identity(*parts):
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:20]


def explicit_codes(scope):
    """Only split scopes that have no qualifications, exclusions or alternatives."""
    folded = scope.casefold()
    if any(word in folded for word in ("кроме", "исключ", "все", "всё", "услов", "испытан", "платн", "соответств", "при ", "если")):
        return []
    if "/" in scope:
        return []
    return sorted({code for code in CODE.findall(scope) if not code.endswith(".00")})


class Catalog:
    def __init__(self, path=DEFAULT_CATALOG, *, quantities=True):
        self.path = Path(path)
        source = json.loads(self.path.read_text(encoding="utf-8"))
        self.sources = {s["id"]: s for s in source["sources"]}
        self.universities = {u["id"]: dict(u) for u in source["universities"]}
        field_names = json.loads((ROOT / "data/fields.json").read_text(encoding="utf-8"))["fields"]
        self.fields = {}
        self.programs = {}
        self.units = {}
        self.olympiads = {}
        self.rules = []
        links = defaultdict(set)
        directory_path = self.path.parent / "programs.json"
        if directory_path.exists():
            directory = json.loads(directory_path.read_text(encoding="utf-8"))
            if directory["admission_year"] != source["admission_year"]:
                raise ValueError("Program directory and rules must belong to the same admission year")
            self.sources.update({s["id"]: s for s in directory["sources"]})
            for p in directory["programs"]:
                self.programs[p["id"]] = dict(p)
                code = p["field_id"]
                self.fields.setdefault(code, {"id": code, "code": code, **field_names.get(code, {"name": p["field_name"], "degree": p["education_level"], "group": "Другие направления"})})
        organization_path = self.path.parent / "organization/catalog.json"
        if organization_path.exists():
            organization = json.loads(organization_path.read_text(encoding="utf-8"))
            if organization["admission_year"] != source["admission_year"]:
                raise ValueError("Organization directory and rules must belong to the same admission year")
            self.sources.update({s["id"]: s for s in organization["sources"]})
            self.units = {u["id"]: dict(u) for u in organization["units"]}
            for p in organization["programs"]:
                self.programs.setdefault(p["id"], {}).update(p)
                code = p["field_id"]
                self.fields.setdefault(code, {"id": code, "code": code, **field_names.get(code, {
                    "name": p.get("field_name", code), "degree": "Бакалавриат" if code[3:5] == "03" else "Специалитет", "group": "Другие направления"})})
        directory_lookup = {(p["university_id"], p["field_id"], normalized(name)): p["id"]
                            for p in self.programs.values() for name in [p["name"]] + p.get("rule_names", [])}
        hse_programs = defaultdict(set)
        for r in source["rules"]:
            v = r["values"]
            if r["university_id"] == "hse" and v.get("field_codes"):
                hse_programs[normalized(v["program_scope"])].add((v["program_scope"], tuple(CODE.findall(v["field_codes"]))))
        for original in source["rules"]:
            rule = dict(original)
            values = rule["values"]
            uid = rule["university_id"]
            name = values.get("olympiad_name") or "Название указано в документе"
            oid = identity(rule["category"], normalized(name))
            olympiad = self.olympiads.setdefault(oid, {"id": oid, "name": name, "category": rule["category"], "profiles": set(), "levels": set(), "aliases": set()})
            olympiad["profiles"].add(values.get("olympiad_profile", ""))
            olympiad["levels"].add(values.get("olympiad_level", ""))
            olympiad["aliases"].add(name)
            scope = values.get("program_scope") or "Общие условия вуза"
            # The HSE source has explicit educational program and field columns.
            candidates = hse_programs.get(normalized(scope), set()) if uid == "hse" else set()
            hse_program = next(iter(candidates)) if len(candidates) == 1 else None
            if uid == "hse" and values.get("field_codes"):
                hse_program = (scope, CODE.findall(values["field_codes"]))
            hse_codes = hse_program[1] if hse_program else []
            codes = list(hse_codes or (explicit_codes(scope) if uid != "hse" else []))
            pids = []
            if codes:
                for code in codes:
                    field = self.fields.setdefault(code, {"id": code, "code": code, **field_names.get(code, {"name": code, "degree": "Бакалавриат" if code[3:5] == "03" else "Специалитет", "group": "Другие направления"})})
                    pname = hse_program[0] if hse_codes else field["name"]
                    pid = directory_lookup.get((uid, code, normalized(pname)), identity(uid, code, pname))
                    self.programs.setdefault(pid, {"id": pid, "university_id": uid, "name": pname, "field_id": code, "kind": "program" if hse_codes else "field"})
                    pids.append(pid)
            else:
                pid = identity(uid, "scope", scope)
                self.programs.setdefault(pid, {"id": pid, "university_id": uid, "name": scope, "field_id": None, "kind": "group"})
                pids.append(pid)
            rule.update(olympiad_id=oid, program_ids=pids, field_ids=codes)
            # Membership connects a program to its school's original conditions;
            # it does not assert that every school benefit applies to the program.
            related = [p for p in self.programs.values() if p["university_id"] == uid and p["id"] not in pids and
                       (p.get("rule_scope") == scope or
                        (p.get("rule_relation") == "field_conditions" and p["field_id"] in codes))]
            rule["related_program_ids"] = [p["id"] for p in related]
            rule["related_field_ids"] = sorted({p["field_id"] for p in related})
            rule["unit_ids"] = sorted({unit_id for pid in pids + rule["related_program_ids"]
                                       for unit_id in self.programs[pid].get("unit_ids", []) + self.programs[pid].get("department_ids", [])})
            rule["search"] = normalized(" ".join(str(v) for v in values.values()) + " " + " ".join(rule.get("conditions", [])))
            self.rules.append(rule)
            links[("u", uid)].add(rule["id"])
            links[("o", oid)].add(rule["id"])
            for unit_id in rule["unit_ids"]:
                links[("t", unit_id)].add(rule["id"])
            for pid in pids:
                links[("p", pid)].add(rule["id"])
            for code in codes:
                links[("f", code)].add(rule["id"])
            for p in related:
                links[("p", p["id"])].add(rule["id"])
                links[("f", p["field_id"])].add(rule["id"])
        self.by_id = {r["id"]: r for r in self.rules}
        directory_fields = {(p["university_id"], p["field_id"]) for p in self.programs.values() if p.get("unit_ids")}
        for p in self.programs.values():
            p.setdefault("unit_ids", [])
            p.setdefault("department_ids", [])
            p["aggregate"] = p["kind"] == "field" and (p["university_id"], p["field_id"]) in directory_fields and not p["unit_ids"]
            p["affiliation_status"] = "verified" if p["unit_ids"] else "scope" if p["kind"] == "group" or p["aggregate"] else "not_in_directory"
        for prefix, entities in (("u", self.universities), ("o", self.olympiads), ("p", self.programs), ("f", self.fields), ("t", self.units)):
            for key, entity in entities.items():
                rules = [self.by_id[rid] for rid in links[(prefix, key)]]
                entity.update(rule_count=len(rules), university_ids=sorted({r["university_id"] for r in rules}), olympiad_ids=sorted({r["olympiad_id"] for r in rules}), benefit_types=sorted({b for r in rules for b in r["benefit_types"]}))
                entity["university_benefits"] = {uid: sorted({b for r in rules if r["university_id"] == uid for b in r["benefit_types"]}) for uid in entity["university_ids"]}
                if prefix in ("p", "t"):
                    entity["university_ids"] = [entity["university_id"]]
                if prefix == "f":
                    entity["university_ids"] = sorted({p["university_id"] for p in self.programs.values() if p["field_id"] == key})
                if prefix == "t":
                    ps = [p for p in self.programs.values() if key in p["unit_ids"] + p["department_ids"]]
                    entity["program_ids"] = [p["id"] for p in ps]
                    entity["program_count"] = len(ps)
                    entity["field_ids"] = sorted({p["field_id"] for p in ps})
                    entity["field_rule_counts"] = {code: sum(code in r["field_ids"] + r["related_field_ids"] for r in rules)
                                                   for code in entity["field_ids"]}
                    entity["child_ids"] = [u["id"] for u in self.units.values() if u["parent_id"] == key]
                if prefix == "o":
                    for k in ("profiles", "levels", "aliases"):
                        entity[k] = sorted(entity[k] - {""})
                    # Its own id is redundant in this projection.
                    del entity["olympiad_ids"]
                if prefix == "u":
                    entity["program_count"] = sum(p["university_id"] == key and p["kind"] != "group" and not p["aggregate"] for p in self.programs.values())
                    entity["field_count"] = len({p["field_id"] for p in self.programs.values() if p["university_id"] == key and p["field_id"]})
                    entity["group_count"] = sum(p["university_id"] == key and p["kind"] == "group" for p in self.programs.values())
                    entity["unit_count"] = sum(u["university_id"] == key and not u["parent_id"] for u in self.units.values())
        self.quantity_data = None
        quantity_path = self.path.parent.parent / '2026-quantities'
        if quantities and (quantity_path / 'catalog.json').exists():
            sys.path.insert(0, str(ROOT.parent / 'data_loader'))
            from admissions.quantity_catalog import load, MANIFEST
            self.quantity_data = load(target=quantity_path, programs=self.programs)
            release = json.loads(MANIFEST.read_text(encoding='utf-8'))['release_tag']
            for q in self.quantity_data['programs']:
                self.programs[q['id']].update(q, quantity_release=release)
        self.bootstrap = {
            "admission_year": source["admission_year"], "collected_on": source["collected_on"],
            "rule_count": len(self.rules), "source_count": len(self.sources),
            "universities": list(self.universities.values()),
            "units": list(self.units.values()),
            "olympiads": sorted(self.olympiads.values(), key=lambda x: normalized(x["name"])),
            "fields": sorted(self.fields.values(), key=lambda x: x["code"]),
            "programs": sorted(self.programs.values(), key=lambda x: (x["field_id"] or "zz", normalized(x["name"]))),
            "quantity_coverage": self.quantity_data['coverage'] if self.quantity_data else None,
        }

    def query(self, params):
        def value(key):
            return params.get(key, [""])[0]
        query = normalized(value("q"))
        filters = {key: value(key) for key in ("university", "unit", "olympiad", "program", "field", "benefit", "category", "profile", "level")}
        rows = []
        for r in self.rules:
            if filters["university"] and r["university_id"] != filters["university"]:
                continue
            if filters["unit"] and filters["unit"] not in r["unit_ids"]:
                continue
            if filters["olympiad"] and r["olympiad_id"] != filters["olympiad"]:
                continue
            if filters["program"] and filters["program"] not in r["program_ids"] + r["related_program_ids"]:
                continue
            if filters["field"] and filters["field"] not in r["field_ids"] + r["related_field_ids"]:
                continue
            if filters["benefit"] and filters["benefit"] not in r["benefit_types"]:
                continue
            if filters["category"] and r["category"] != filters["category"]:
                continue
            if filters["profile"] and r["values"].get("olympiad_profile") != filters["profile"]:
                continue
            if filters["level"] and r["values"].get("olympiad_level") != filters["level"]:
                continue
            if query and not all(word in r["search"] for word in query.split()):
                continue
            rows.append(r)
        limit = max(1, min(100, int(value("limit") or "24")))
        offset = max(0, int(value("offset") or "0"))
        return {"total": len(rows), "offset": offset, "limit": limit, "items": [self.public_rule(r) for r in rows[offset:offset + limit]]}

    def public_rule(self, rule):
        result = {k: v for k, v in rule.items() if k != "search"}
        source = self.sources[rule["source_id"]]
        page = rule.get("location", {}).get("page")
        result["source"] = {"title": source.get("title") or "Официальный документ", "url": source["url"], "local_url": "/sources/" + source["id"] + (f"#page={page}" if page and source["file"].endswith(".pdf") else "")}
        return result
