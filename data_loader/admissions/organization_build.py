"""Build the university/unit/program graph from saved official directories.

No affiliations are inferred from a field's subject or a department's number.
Every edge is backed by a university directory, program page or admission table.
"""
import hashlib
import html
import json
import re
from collections import defaultdict
from urllib.parse import urljoin

from lxml import html as dom
import json5

from .organization import ROOT
from .paths import SNAPSHOT

CODE = re.compile(r"\d{2}\.\d{2}\.\d{2}")


def clean(value):
    if not isinstance(value, str):
        value = value.text_content()
    return " ".join(html.unescape(value).split())


def identity(*parts):
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:20]


class Builder:
    def __init__(self):
        self.sources, self.units, self.programs = {}, {}, {}

    def source(self, key):
        if key not in self.sources:
            m = json.loads((ROOT / "sources" / (key + ".meta.json")).read_text(encoding="utf-8"))
            path = ROOT / "sources" / m["file"]
            assert hashlib.sha256(path.read_bytes()).hexdigest() == m["sha256"], key
            self.sources[key] = {**m, "file": "organization/sources/" + m["file"]}
        return self.sources[key]

    def read(self, key):
        return (SNAPSHOT / self.source(key)["file"]).read_text(encoding="utf-8")

    def page(self, key):
        return dom.fromstring(self.read(key))

    def unit(self, university, key, name, source, url=None, code=None, parent=None, kind=None):
        uid = university + "-" + str(key)
        name = clean(name)
        if not kind:
            low = name.lower()
            kind = next((t for t in ["факультет", "институт", "школа", "кафедра", "центр", "департамент"] if t in low), "подразделение")
        record = self.units.setdefault(uid, dict(id=uid, university_id=university, name=name, type=kind,
                    code=code, parent_id=parent, source_ids=[], url=url or self.source(source)["url"]))
        if source not in record["source_ids"]:
            record["source_ids"].append(source)
        self.source(source)
        return uid

    def program(self, university, code, name, unit_ids, source, locator, **extra):
        assert CODE.fullmatch(code), (university, code, name)
        name = clean(name)
        pid = extra.pop("id", identity(university, code, name))
        record = self.programs.setdefault(pid, dict(id=pid, university_id=university, field_id=code,
                    name=name, kind="program", unit_ids=[], affiliations=[], source_id=source,
                    source_url=self.source(source)["url"], **extra))
        for uid in unit_ids:
            assert uid in self.units
            if uid not in record["unit_ids"]:
                record["unit_ids"].append(uid)
            edge = dict(unit_id=uid, source_id=source, locator=locator)
            if edge not in record["affiliations"]:
                record["affiliations"].append(edge)
        return record

    def hse_state(self, key):
        scripts = self.page(key).xpath('//script[contains(text(), "window.__INITIAL_STATE__ =")]/text()')
        assert len(scripts) == 1
        return json5.loads(scripts[0].split("=", 1)[1].split(";window.__URQL_DATA__", 1)[0])

    def hse(self):
        state = self.hse_state("hse_all")
        all_programs = state["bachelorPrograms"]
        assert len(all_programs["items"]) == all_programs["total"]
        seen = set()
        for u in state["bachelorFilters"]["orgUnits"]:
            if u["campus"]["id"] != 51999662:
                continue
            key = "hse_unit_" + str(u["id"])
            state = self.hse_state(key)
            assert state["bachelorState"]["orgUnits"] == [u["id"]]
            listing = state["bachelorPrograms"]
            assert len(listing["items"]) == listing["total"]
            if not listing["items"]:
                continue
            uid = self.unit("hse", u["id"], u["title"], key)
            for p in listing["items"]:
                seen.add(p["id"])
                assert p["campusLabel"] == "Москва"
                self.program("hse", p["direction"]["directionNumber"], p["title"], [uid], key,
                    "bachelorPrograms.items id=" + str(p["id"]), program_url=p["url"],
                    field_name=p["direction"]["title"], education_level=p["typeLabel"], rule_relation="exact_program")
        for p in all_programs["items"]:
            if p["id"] in seen:
                continue
            # HSE's unit filter omits secondary field-code entries for two
            # joint programs. The complete directory links them to exactly the
            # same named program URL. Keep codes (and their benefit rules) separate.
            peers = [q for q in self.programs.values() if q["university_id"] == "hse"
                     and q["name"] == clean(p["title"]) and q.get("program_url") == p["url"]]
            assert peers, p
            units = sorted({u for q in peers for u in q["unit_ids"]})
            self.program("hse", p["direction"]["directionNumber"], p["title"], units, "hse_all",
                "bachelorPrograms.items id=" + str(p["id"]) + "; same named program URL in unit directories",
                program_url=p["url"], field_name=p["direction"]["title"], education_level=p["typeLabel"], rule_relation="exact_program")
        # Reviewed spelling/format differences between the 2026 benefit tables
        # and the program directory. Matching still requires the exact field code.
        aliases = {
            "Совместный бакалавриат НИУ ВШЭ и ЦПМ": "Совместный бакалавриат НИУ ВШЭ и Центра педагогического мастерства",
            "Компьютерные науки и анализ данных": "Компьютерные науки и анализ данных (онлайн)",
            "Экономический анализ": "Экономический анализ (онлайн)",
            "Международный бизнес": "Международный бизнес (реализуется на английском языке)",
            "Программа двух дипломов НИУ ВШЭ и Университета Кёнхи «Экономика и политика в Азии»": "Программа двух дипломов НИУ ВШЭ и Университета Кёнхи «Экономика и политика в Азии» (реализуется на английском языке)",
            "Международная программа «Международные отношения и глобальные исследования»": "Международная программа «Международные отношения и глобальные исследования» (реализуется на английском языке)",
        }
        for p in self.programs.values():
            if p["university_id"] == "hse" and p["name"] in aliases:
                p["rule_names"] = [aliases[p["name"]]]

    def itmo(self):
        listing = json.loads(self.read("itmo_short"))
        groups = listing["result"]["groups"]
        assert len(groups) == listing["meta_data"]["total"]
        for g in groups:
            assert g["year"] == 2026
            key = "itmo_" + g["slug"]
            anchors = self.page(key).xpath('//a[@href]')
            matches = [a for a in anchors if clean(a) and
                       ("/viewfaculty/" in a.get("href") or "shkola_razrabotki_videoigr" in a.get("href") or
                        ("fitp.itmo.ru" in a.get("href") and "факультет" in clean(a).lower()))]
            unit_ids = []
            for a in matches:
                name = clean(a)
                if name.lower() in [self.units[u]["name"].lower() for u in unit_ids]:
                    continue
                uid = self.unit("itmo", identity(name.lower()), name[0].upper() + name[1:], key, a.get("href"))
                unit_ids.append(uid)
            assert len(unit_ids) == 1, (key, unit_ids)
            for p in g["programs"]:
                code = p["direction_code"]
                self.program("itmo", code, g["name"], unit_ids, key, "program page; group id=" + str(g["id"]),
                    program_url=self.source(key)["url"], rule_relation="field_conditions")

    def bmstu(self):
        listing = json.loads(self.read("bmstu_majors"))
        assert len(listing["data"]) == listing["meta"]["count"]
        for p in listing["data"]:
            units, departments = [], []
            for f in p["faculties"]:
                name = f["title"] if "Кафедра" in f["title"] else "Факультет «" + f["title"] + "»"
                uid = self.unit("bmstu", f["slug"], name, "bmstu_majors", "https://bmstu.ru/faculty/" + f["slug"], f["code"])
                units.append(uid)
                for c in f["chairs"]:
                    # The API's ЮР entry denotes a specialty, not a second department.
                    if c["code"] == f["code"]:
                        continue
                    cid = self.unit("bmstu", "chair-" + c["slug"], "Кафедра «" + clean(c["title"]) + "»",
                        "bmstu_majors", "https://bmstu.ru/chair/" + c["slug"], c["code"], uid, "кафедра")
                    departments.append(cid)
            codes, names = CODE.findall(p["code"]), p["name"].split(" / ")
            assert len(codes) == len(names), p
            for code, name in zip(codes, names):
                self.program("bmstu", code, name, units, "bmstu_majors", "data slug=" + p["slug"],
                    directory_kind="field", department_ids=departments, program_url="https://bmstu.ru/bachelor/majors/" + p["slug"],
                    education_level="Базовое высшее образование" if p["qualification"] == "пилотный проект" else p["qualification"],
                    rule_relation="field_conditions")

    def mipt(self):
        names = {}
        for text in self.page("mipt_rules").xpath('//span/text()'):
            match = re.fullmatch(r"((?:Физтех-школа|Высшая школа) .+) \(([^()]+)\)", clean(text))
            if match:
                names[match[2]] = match[1]
        existing = json.loads((SNAPSHOT / "programs.json").read_text(encoding="utf-8"))
        for p in existing["programs"]:
            if p["university_id"] != "mipt":
                continue
            school = p["school"]
            if school == "ФБМФ, ВШБИ":
                options = [x for x in ["ФБМФ", "ВШБИ"] if x in p["name"]]
                assert len(options) == 1, p
                school = options[0]
            uid = self.unit("mipt", identity(school), names[school], "mipt_rules", code=school)
            # The original rule_scope remains combined where the benefit document combines schools.
            extra = {k: v for k, v in p.items() if k not in ["name", "field_id", "university_id", "source_id", "source_url", "kind"]}
            record = self.program("mipt", p["field_id"], p["name"], [uid], "mipt_rules", "section " + school, **extra)
            record.update(source_id=p["source_id"], source_url=p["source_url"])

    def mai(self):
        directories = {}
        for a in self.page("mai_institutes").xpath('//a[contains(@class,"card-order-")]'):
            number = re.search(r"card-order-(\d+)", a.get("class"))[1]
            url, name = a.get("href"), clean(a)
            if number in ["13"]:  # military training does not define a standalone admission program
                continue
            slug = url.rstrip("/").rsplit("/", 1)[-1]
            key = "mai_institute_" + number
            uid = self.unit("mai", slug, ("Институт №" + number + " «" + name + "»") if int(number) <= 12 else name,
                            "mai_institutes", url, number)
            departments = {}
            for link in self.page(key).xpath('//a[@href]'):
                m = re.fullmatch(r"Кафедра (\d+[А-Яа-яБ]?)", clean(link))
                if m:
                    departments[m[1]] = urljoin(url, link.get("href"))
            directories[slug] = (uid, departments, key)
        for index, p in enumerate(self.page("mai_programs").xpath('//*[@data-program]'), 1):
            slug, department = p.get("data-fac"), p.get("data-kaf")
            if slug in ["strela", "stupino", "voshod", "vzlet"]:
                continue  # explicitly separate branches in the official catalog
            # The admission catalog calls the advanced school "advanced".
            if slug == "advanced" and slug not in directories:
                options = [v for k, v in directories.items() if self.units[v[0]]["code"] == "14"]
                assert len(options) == 1
                directories[slug] = options[0]
            uid, departments, key = directories[slug]
            anchor = p.xpath('.//a[contains(@class,"program-main")]')[0]
            code = clean(p.xpath('.//*[contains(@class,"program-code")]')[0])
            department_ids = []
            if department in departments:
                cid = self.unit("mai", "chair-" + department, "Кафедра " + department, key,
                                departments[department], department, uid, "кафедра")
                department_ids.append(cid)
            self.program("mai", code, clean(anchor), [uid], "mai_programs", "data-program row=" + str(index),
                department_ids=department_ids, department_label=clean(p.xpath('.//*[contains(@class,"program-department")]')[0]),
                program_url=urljoin(self.source("mai_programs")["url"], anchor.get("href")), rule_relation="field_conditions")

    def mephi(self):
        tables = self.page("mephi_programs").xpath('//table')
        assert len(tables) == 2
        for number, table in enumerate(tables, 1):
            self.mephi_table(table, number)

    def mephi_table(self, table, number):
        cells = {}
        for row_index, tr in enumerate(table.xpath('.//tr[td]')):
            col = 0
            for td in tr.xpath('./td'):
                while (row_index, col) in cells:
                    col += 1
                for rr in range(int(td.get("rowspan", 1))):
                    for cc in range(int(td.get("colspan", 1))):
                        assert (row_index + rr, col + cc) not in cells
                        cells[row_index + rr, col + cc] = td
                col += int(td.get("colspan", 1))
            row = [cells.get((row_index, i)) for i in range(5)]
            if row[0] is None or not CODE.fullmatch(clean(row[0])):
                continue
            assert all(x is not None for x in row), row_index
            units = []
            anchors = row[2].xpath('.//a[@href]')
            assert anchors, clean(row[2])
            for a in anchors:
                name = clean(a)
                if not name:
                    continue
                uid = self.unit("mephi", identity(name.lower()), name, "mephi_programs", urljoin(self.source("mephi_programs")["url"], a.get("href")))
                units.append(uid)
            assert units
            name = clean(row[3])
            assert name
            a = row[3].xpath('.//a[@href]')
            self.program("mephi", clean(row[0]), name, units, "mephi_programs", f"table={number} row=" + str(row_index + 2),
                program_url=urljoin(self.source("mephi_programs")["url"], a[0].get("href")) if a else self.source("mephi_programs")["url"],
                rule_relation="field_conditions")

    def msal(self):
        self.source("msal_tracks")
        # Extracted with pdfplumber; both pages visually checked against the PDF.
        extraction = json.loads((ROOT / "sources/msal_tracks.extracted.json").read_text(encoding="utf-8"))
        assert extraction["source_sha256"] == self.source("msal_tracks")["sha256"], "Re-extract the changed MSAL PDF"
        pages = extraction["pages"]
        for page, content in enumerate(pages, 1):
            previous = [None] * 5
            for index, row in enumerate(content["tables"][0][1:], 2):
                row = [value if value is not None else previous[i] for i, value in enumerate(row)]
                previous = row
                field, profile, track, name, address = map(clean, row)
                uid = self.unit("msal", identity(name), name, "msal_tracks")
                code = CODE.search(field)[0]
                profile = profile.replace("Государственно- правовая", "Государственно-правовая")
                if "на базе высшего" in field:
                    profile += " (на базе высшего образования)"
                p = self.program("msal", code, profile, [uid], "msal_tracks", f"page={page} table=1 row={index}",
                    tracks=[], rule_relation="field_conditions", address=address)
                if track not in ["", "–", "_"] and track not in p["tracks"]:
                    p["tracks"].append(track)

    def build(self):
        for method in [self.hse, self.itmo, self.bmstu, self.mipt, self.mai, self.mephi, self.msal]:
            method()
        used = {u for p in self.programs.values() for u in p["unit_ids"] + p.get("department_ids", [])}
        self.units = {k: u for k, u in self.units.items() if k in used}
        result = dict(schema_version=1, admission_year=2026,
            sources=sorted(self.sources.values(), key=lambda s: s["id"]),
            units=sorted(self.units.values(), key=lambda u: u["id"]),
            programs=sorted(self.programs.values(), key=lambda p: p["id"]))
        (ROOT / "catalog.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        for university in ["hse", "itmo", "bmstu", "mipt", "mephi", "mai", "msal"]:
            ps = [p for p in result["programs"] if p["university_id"] == university]
            us = [u for u in result["units"] if u["university_id"] == university]
            print(university, len([u for u in us if not u["parent_id"]]), "units,", len(ps), "program/field entries,", len({p["field_id"] for p in ps}), "fields")
        return result


if __name__ == "__main__":
    Builder().build()
