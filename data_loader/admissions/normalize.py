"""Normalize official tables without discarding their conditions or source locators.

Textual conditions are authoritative. This is a data catalogue, not an automatic
eligibility decision engine: school-specific and statutory exceptions stay explicit.
"""
import hashlib
import json
import re
from collections import Counter
from .sources import SNAPSHOT, clean

UNIVERSITIES = [
    {"id": "hse", "name": "Национальный исследовательский университет «Высшая школа экономики»", "short_name": "НИУ ВШЭ", "city": "Москва", "site": "https://www.hse.ru", "scope": "Московский кампус, 67 образовательных программ"},
    {"id": "itmo", "name": "Национальный исследовательский университет ИТМО", "short_name": "ИТМО", "city": "Санкт-Петербург", "site": "https://itmo.ru", "scope": "Бакалавриат"},
    {"id": "bmstu", "name": "Московский государственный технический университет имени Н. Э. Баумана", "short_name": "МГТУ им. Баумана", "city": "Москва", "site": "https://bmstu.ru", "scope": "Московский кампус; приложение 5.2 для филиалов не применяется"},
    {"id": "mipt", "name": "Московский физико-технический институт (национальный исследовательский университет)", "short_name": "МФТИ", "city": "Долгопрудный", "site": "https://mipt.ru", "scope": "Физтех-школы и конкурсные группы из правил 2026"},
    {"id": "mephi", "name": "Национальный исследовательский ядерный университет «МИФИ»", "short_name": "НИЯУ МИФИ", "city": "Москва", "site": "https://mephi.ru", "scope": "Московский кампус; таблица филиалов не применяется"},
    {"id": "mai", "name": "Московский авиационный институт (национальный исследовательский университет)", "short_name": "МАИ", "city": "Москва", "site": "https://mai.ru", "scope": "Направления и специальности приложения 7"},
    {"id": "msal", "name": "Московский государственный юридический университет имени О. Е. Кутафина (МГЮА)", "short_name": "МГЮА", "city": "Москва", "site": "https://msal.ru", "scope": "40.03.01, 40.05.01, 40.05.03, 40.05.04"},
]


def load(key):
    return json.loads((SNAPSHOT / "sources" / (key + ".json")).read_text(encoding="utf-8"))


def expand_html(rows):
    """Expand rowspan/colspan, preserving empty cells (empty is not inheritance)."""
    grid = {}
    width = 0
    for y, row in enumerate(rows):
        x = 0
        for cell in row:
            while (y, x) in grid:
                x += 1
            for dy in range(cell["rowspan"]):
                for dx in range(cell["colspan"]):
                    if (y + dy, x + dx) in grid:
                        raise ValueError("Overlapping HTML table spans")
                    grid[y + dy, x + dx] = cell["text"]
            x += cell["colspan"]
            width = max(width, x)
    return [[grid.get((y, x), "") for x in range(width)] for y in range(len(rows))]


def pdf_rows(source, width):
    for page in source["pages"]:
        for ti, table in enumerate(page["tables"], 1):
            for ri, cells in enumerate(table, 1):
                if len(cells) == width:
                    yield {"page": page["page"], "table": ti, "row": ri}, cells


def record(source, location, values, kinds, category="rsosh", conditions=None):
    identity = [source["id"], location, values, kinds, category]
    key = hashlib.sha256(json.dumps(identity, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:24]
    return {
        "id": key, "admission_year": 2026, "university_id": source["university"],
        "category": category, "benefit_types": kinds,
        "source_id": source["id"], "source_url": source["url"], "location": location,
        "values": {k: clean(v) for k, v in values.items()}, "conditions": conditions or [],
    }


def inherit(cells, previous):
    return [clean(c) if clean(c) else previous[i] for i, c in enumerate(cells)]


def hse():
    result = []
    programs = json.loads((SNAPSHOT / "hse_programs.json").read_text(encoding="utf-8"))
    for program in programs:
        source = load(program["source_id"])
        previous = [""] * 9
        for page in source["pages"]:
            for ti, table in enumerate(page["tables"], 1):
                for ri, original in enumerate(table, 1):
                    if len(original) not in (9, 10, 11):
                        continue
                    cells = original[-9:]
                    if not any("Право" in clean(x) for x in cells[5:6]):
                        continue
                    cells = inherit(cells, previous)
                    previous = cells
                    values = dict(zip(("olympiad_name", "olympiad_profile", "olympiad_subject", "confirmation_subjects", "confirmation_score", "benefit", "full_score_subjects", "diplomas", "grades"), cells))
                    values.update(program_scope=program["name"], field_codes=program["field_code"])
                    result.append(record(source, {"page": page["page"], "table": ti, "row": ri}, values,
                                         ["bvi"] if "БВИ" in cells[5] else ["100_points"],
                                         conditions=["Профиль должен входить в перечень в год проведения олимпиады.",
                                                     "Для категории лиц, указанной в сноске ** документа, порог подтверждения составляет 65 баллов."]))
    return result


def itmo():
    result = []
    for key, kind in (("itmo_bvi", "bvi"), ("itmo_100", "100_points")):
        source = load(key)
        rows = list(pdf_rows(source, 6))
        previous = [""] * 6
        for i, (loc, original) in enumerate(rows):
            cells = [clean(c) for c in original]
            if not any(x in cells[5].lower() for x in ("побед", "призер")):
                continue
            # A field list can continue at the top of the next page.
            scope = cells[0]
            if scope and re.search(r"\d{2}\.\d{2}\.\d{2}", scope):
                for nextloc, tail in rows[i + 1:]:
                    if clean(tail[0]):
                        if not clean(tail[1]) and not clean(tail[2]) and not clean(tail[5]):
                            scope += " " + clean(tail[0])
                        break
                cells[0] = scope
            cells = inherit(cells, previous)
            previous = cells
            values = dict(zip(("program_scope", "olympiad_name", "olympiad_profile", "confirmation_subjects", "olympiad_level", "diplomas"), cells))
            values.update(confirmation_score="75", grades="10, 11", benefit="БВИ" if kind == "bvi" else "100 баллов")
            if kind == "100_points":
                values["full_score_subjects"] = cells[3]
            result.append(record(source, loc, values, [kind], conditions=["Ограничения в скобках в профиле олимпиады относятся к области действия этой строки."]))
    return result


def mipt():
    source = load("mipt")
    result = []
    schools = [cell["text"] for cell in source["tables"][1][1]]
    conditions = [
        "Результат олимпиады не ранее 2022 года. Для РСОШ — задания за 11 класс.",
        "Победителям «Физтеха» доступны особые права также за 10 класс (пункт 5).",
        "Победителям Всероссийской олимпиады по искусственному интеллекту за 10 класс — для программ ВШПИ (пункт 6).",
        "Точный порог ЕГЭ/ВИ, степень диплома и конкурсная группа указаны в поле benefit; условия каждой альтернативы применяются совместно.",
    ]
    for ri, row in enumerate(expand_html(source["tables"][1])[2:], 3):
        if not row[0].isdigit():
            continue
        common = dict(zip(("registry_number", "olympiad_name", "olympiad_profile", "olympiad_level"), row[:4]))
        for col in range(4, len(row)):
            if not row[col].strip() or row[col].strip() in ("-", "—"):
                continue
            values = dict(common, benefit=row[col], program_scope="Конкурсные группы МФТИ; см. условия" if col == 4 else schools[col - 5],
                          grades="11; исключения за 10 класс: пункты 5 и 6")
            result.append(record(source, {"table": 2, "row": ri, "column": col + 1}, values,
                                 ["100_points"] if col == 4 else ["bvi"], conditions=conditions))
    for table_index, category in ((2, "vsosh"), (3, "international")):
        for ri, row in enumerate(expand_html(source["tables"][table_index])[2:], 3):
            for col, cell in enumerate(row[1:], 1):
                if cell.strip() and cell.strip() not in ("-", "—"):
                    result.append(record(source, {"table": table_index + 1, "row": ri, "column": col + 1},
                                         {"olympiad_name": row[0], "olympiad_profile": row[0], "program_scope": schools[col - 1], "benefit": cell},
                                         ["bvi"], category, ["Без подтверждения ЕГЭ. Результат не ранее 2022 года; см. пункты 2–3, 11–12."]))
    return result


def mephi():
    source = load("mephi_winners")
    result = []
    for ri, cells in enumerate(expand_html(source["tables"][0])[1:], 2):
        if not any(clean(c["text"]) for c in source["tables"][0][ri - 1]):
            continue
        if not cells[0].isdigit():
            continue
        common = dict(zip(("registry_number", "olympiad_name", "olympiad_level"), cells[:3]))
        common.update(olympiad_profile=cells[6], confirmation_subjects=cells[5], confirmation_score="75", diplomas="Победители и призеры")
        for col, kind in ((3, "bvi"), (4, "100_points")):
            if not cells[col].strip():
                continue
            values = dict(common, program_scope=cells[col], grades="10, 11" if col == 3 else "8, 9, 10, 11", benefit="БВИ" if col == 3 else "100 баллов")
            if col == 4:
                values["full_score_subjects"] = cells[5]
            result.append(record(source, {"table": 1, "row": ri, "column": col + 1}, values, [kind], conditions=[
                "Несколько предметов подтверждаются по одному из них по выбору; 100 баллов засчитываются по этому предмету.",
                "Разделенные косой чертой наборы направлений и предметов сопоставляются по порядку, не как декартово произведение.",
                "Срок — четыре года после года проведения; для участников СВО продлевается на срок участия.",
                "Имеющий БВИ может использовать 100 баллов по предмету олимпиады в основном конкурсе."]))
    return result


def mai():
    source = load("mai_olympiads")
    # Numbered rows are complete records; unnumbered rows at page starts are
    # continuations of the same row, including split program exclusions.
    joined = []
    candidates = list(pdf_rows(source, 7)) + list(pdf_rows(source, 9))
    candidates.sort(key=lambda pair: (pair[0]["page"], pair[0]["table"], pair[0]["row"]))
    for loc, cells in candidates:
        if len(cells) == 9:
            cells = cells[:3] + [" ".join(clean(x) for x in cells[3:6])] + cells[6:]
        cells = [clean(c) for c in cells]
        if cells[0].isdigit():
            joined.append([loc, cells])
        elif joined and not cells[0] and any(cells):
            joined[-1][1] = [clean(a + " " + b) for a, b in zip(joined[-1][1], cells)]
    result = []
    for loc, cells in joined:
        values = dict(zip(("document_number", "registry_number", "olympiad_name", "olympiad_profile", "confirmation_subjects", "olympiad_level", "program_scope"), cells))
        values.update(confirmation_score="75", grades="10, 11", diplomas="Победители и призеры", benefit="БВИ; право на 100 баллов при участии в основном конкурсе", olympiad_year="2025/26")
        result.append(record(source, loc, values, ["bvi", "100_points"], conditions=[
            "Предмет и профиль должны соответствовать одному из вступительных испытаний (кроме русского языка) и выбранному направлению.",
            "Исключения направлений перечислены в program_scope; слово «все» не отменяет эти исключения.",
            "Условия за 10–11 класс и использования 100 баллов — официальная страница https://priem.mai.ru/base/bvi/."]))
    for loc, cells in pdf_rows(source, 3):
        if clean(cells[0]).isdigit():
            category = "international" if "международных олимпиад" in source["pages"][loc["page"] - 1]["text"] else "vsosh"
            result.append(record(source, loc, {"olympiad_name": "Международные олимпиады" if category == "international" else "Всероссийская олимпиада школьников", "olympiad_profile": cells[1], "program_scope": cells[2], "benefit": "БВИ", "diplomas": "Победители и призеры"}, ["bvi"], category, ["ЕГЭ для подтверждения не требуется; диплом действует четыре года."]))
    return result


def msal():
    source = load("msal_rights")
    rows = []
    for loc, cells in pdf_rows(source, 8):
        cells = [clean(c) for c in cells]
        if not cells[0] and not cells[6] and rows and any(cells):
            rows[-1][1] = [clean(a + " " + b) for a, b in zip(rows[-1][1], cells)]
        elif re.fullmatch(r"\d+\.?", cells[0]) or cells[6] in ("10", "11"):
            rows.append([loc, cells])
    previous = [""] * 8
    result = []
    for loc, row in rows:
        cells = inherit(row, previous)
        previous = cells
        values = dict(zip(("document_number", "olympiad_name", "olympiad_profile", "confirmation_subjects", "program_scope", "confirmation_score", "grades", "benefit"), cells))
        for before, after in (("оли мпиад", "олимпиад"), ("Все российская", "Всероссийская"),
                              ("шко льник", "школьник"), ("Пет ербург", "Петербург"),
                              ("Санкт- Петербург", "Санкт-Петербург"), ("обра зователь", "образователь"),
                              ("Мос ковская", "Московская"), ("Оке ан", "Океан"), ("МИ Д", "МИД")):
            values["olympiad_name"] = values["olympiad_name"].replace(before, after)
        values["full_score_subjects"] = cells[3]
        values["diplomas"] = "Победители и призеры"
        kinds = ["100_points"]
        if "прием без" in cells[7]:
            kinds.insert(0, "bvi")
        result.append(record(source, loc, values, kinds, conditions=["Для зачисления действуют общие условия особых прав на странице 1; срок — четыре года после года проведения."]))
    return result


def additional_vsosh():
    result = []
    source = load("hse_vsosh")
    for ri, row in enumerate(expand_html(source["tables"][0])[1:], 2):
        if not row[0].isdigit():
            continue
        for col, kind in ((2, "bvi"), (3, "100_points")):
            if row[col] and row[col] not in ("—", "-"):
                result.append(record(source, {"table": 1, "row": ri, "column": col + 1},
                                     {"olympiad_name": "Всероссийская олимпиада школьников", "olympiad_profile": row[col],
                                      "program_scope": row[1], "benefit": "БВИ" if col == 2 else "100 баллов"}, [kind], "vsosh",
                                     ["Победители и призеры заключительного этапа. Сохранены отдельные условия для дипломов информатики 2026 года и более ранних дипломов."]))
    source = load("bmstu_201")
    kind = "100_points"
    for loc, cells in pdf_rows(source, 2):
        cells = [clean(c) for c in cells]
        if cells[0] == "Профиль ВОШ":
            kind = "bvi" if "без вступительных" in cells[1] else "100_points"
            continue
        if not all(cells):
            continue
        values = {"olympiad_name": "Всероссийская олимпиада школьников", "olympiad_profile": cells[0],
                  "program_scope": cells[1] if kind == "bvi" else "НПС с соответствующим вступительным испытанием",
                  "benefit": "БВИ" if kind == "bvi" else "100 баллов", "diplomas": "Победители и призеры"}
        if kind == "100_points":
            values["full_score_subjects"] = cells[1]
        result.append(record(source, loc, values, [kind], "vsosh"))
    source = load("msal_rights")
    for subject in ("Право", "Обществознание", "История", "Русский язык", "Иностранный язык"):
        result.append(record(source, {"page": 1, "section": "1", "paragraph": 1},
                             {"olympiad_name": "Всероссийская олимпиада школьников", "olympiad_profile": subject,
                              "program_scope": "40.03.01, 40.05.01, 40.05.03, 40.05.04", "benefit": "БВИ и особое преимущество 100 баллов по обществознанию",
                              "full_score_subjects": "Обществознание"}, ["bvi", "100_points"], "vsosh",
                             ["Пункт 1 документа об особых правах; срок — четыре года после года олимпиады. Используется основной документ, а не сокращенная памятка."]))
    source = load("itmo_vsosh")
    joined = []
    current_page = None
    started_page = False
    for loc, cells in pdf_rows(source, 2):
        cells = [clean(c) for c in cells]
        if loc["page"] != current_page:
            current_page, started_page = loc["page"], False
        if re.search(r"\d{2}\.\d{2}\.\d{2}", cells[0]):
            started_page = True
        if not started_page:
            continue
        if cells[0].startswith("Направление") or "Министерство" in " ".join(cells) or "федеральное государственное" in " ".join(cells):
            continue
        if joined and (not all(cells) or joined[-1][1][1].endswith(",")):
            joined[-1][1] = [clean(a + " " + b) for a, b in zip(joined[-1][1], cells)]
        elif all(cells):
            joined.append([loc, cells])
    for loc, cells in joined:
        result.append(record(source, loc, {"olympiad_name": "Всероссийская олимпиада школьников / международные олимпиады",
                             "olympiad_profile": cells[1], "program_scope": cells[0], "benefit": "БВИ"}, ["bvi"], "vsosh",
                             ["Заключительный этап ВсОШ; документ также устанавливает соответствие для международных олимпиад."]))
    for key, kind in (("mephi_vsosh_bvi", "bvi"), ("mephi_vsosh_100", "100_points")):
        source = load(key)
        for loc, cells in pdf_rows(source, 2):
            cells = [clean(c) for c in cells]
            if cells[0] == "Профиль" or not all(cells):
                continue
            result.append(record(source, loc, {"olympiad_name": "Всероссийская олимпиада школьников", "olympiad_profile": cells[0],
                                 "program_scope": cells[1] if kind == "bvi" else "Направления с соответствующим вступительным испытанием",
                                 "benefit": "БВИ" if kind == "bvi" else "100 баллов", "full_score_subjects": cells[1] if kind == "100_points" else ""}, [kind], "vsosh",
                                 ["Таблица утверждена приемной комиссией 16.01.2026; слово proekt в имени файла не является статусом документа."]))
    return result


def bmstu():
    result = []
    canonical_names = {}
    normalized = lambda value: re.sub(r"[^а-яa-z0-9]", "", clean(value).lower().replace("ё", "е"))
    for key, kind in (("bmstu_190", "bvi"), ("bmstu_315", "100_points")):
        source = load(key)
        year = "2025/26"
        scope = "Направления, на которых выбранный предмет входит во вступительные испытания"
        rows = []
        for page in source["pages"]:
            for ti, table in enumerate(page["tables"], 1):
                table_year = page.get("table_years", [None] * len(page["tables"]))[ti - 1]
                if table_year:
                    year = table_year
                for ri, original in enumerate(table, 1):
                    if len(original) != 8:
                        continue
                    cells = [clean(c) for c in original]
                    if cells[0].startswith("Для направлен"):
                        scope = cells[0]
                        continue
                    if not any(c.lower() in ("предоставляется", "не предоставляется") for c in cells[6:]):
                        continue
                    rows.append({"loc": {"page": page["page"], "table": ti, "row": ri}, "cells": cells, "original": original,
                                 "scope": scope, "year": year})
        # Reconstruct identities of vertically merged blocks crossing a page.
        explicit_names = {}
        for entry in rows:
            if entry["cells"][0].isdigit() and entry["cells"][1]:
                explicit_names.setdefault((entry["year"], entry["cells"][0]), []).append(entry["cells"][1])
        number = ""
        for i, entry in enumerate(rows):
            row = entry["cells"]
            raw = entry["original"]
            if row[0].isdigit():
                number = row[0]
            elif raw[0] is not None and (row[1] or entry["loc"]["row"] > 1):
                possible = explicit_names.get((entry["year"], number), []) + [canonical_names.get((entry["year"], number), "")]
                is_continuation = bool(row[1]) and any(normalized(row[1]) in normalized(name) for name in possible)
                if not is_continuation:
                    following = next((x["cells"][0] for x in rows[i + 1:] if x["cells"][0].isdigit()), "")
                    if following:
                        number = following
            entry["number"] = number
        names = {}
        for entry in rows:
            key_name = (entry["year"], entry["number"])
            name = entry["cells"][1]
            if name:
                names.setdefault(key_name, []).append(name)
        for entry in rows:
            cells = entry["cells"]
            variants = names.get((entry["year"], entry["number"]), [])
            prior_name = canonical_names.get((entry["year"], entry["number"]), "")
            if prior_name:
                variants = variants + [prior_name]
            name = max(variants, key=len, default="")
            for fragment in variants:
                if fragment and normalized(fragment) not in normalized(name) and len(fragment) < len(name) / 2:
                    name = clean(name + " " + fragment)
            canonical_names[entry["year"], entry["number"]] = name
            values = dict(registry_number=entry["number"], olympiad_name=name,
                          olympiad_profile=cells[2], olympiad_subject=cells[3], olympiad_level=cells[4],
                          confirmation_subjects=cells[5], confirmation_score="75", grades="10, 11",
                          program_scope=entry["scope"], olympiad_year=entry["year"],
                          winner=cells[6], prize_winner=cells[7], benefit="БВИ" if kind == "bvi" else "100 баллов")
            if kind == "100_points":
                values["full_score_subjects"] = cells[5]
            result.append(record(source, entry["loc"], values, [kind], conditions=[
                "Степень диплома: winner — победитель (I); prize_winner — призер (II–III). «Не предоставляется» означает отсутствие права.",
                "При нескольких предметах выбирается один и подтверждается ЕГЭ по нему (приложение 5, пункт 3).",
                "Для категории лиц из пункта 8 приложения 5 порог ЕГЭ — 65 баллов.",
                "Обладателям БВИ доступно особое преимущество 100 баллов на остальных направлениях (пункт 7 приложения 5).",
                "Названия и номера сопоставляются только внутри одного года перечня; полный текст и исходные ячейки сохранены в источнике."]))
    return result


def build():
    rules = []
    for parser in (hse, itmo, bmstu, mipt, mephi, mai, msal, additional_vsosh):
        items = parser()
        if not items:
            raise ValueError(f"No rules for {parser.__name__}")
        rules.extend(items)
    sources = []
    for path in sorted((SNAPSHOT / "sources").glob("*.json")):
        source = json.loads(path.read_text(encoding="utf-8"))
        sources.append({k: v for k, v in source.items() if k not in ("text", "tables", "pages", "links")})
    dataset = {"schema_version": 1, "admission_year": 2026, "collected_on": "2026-09-06",
               "universities": UNIVERSITIES, "sources": sources, "rules": rules}
    from .loader import validate
    validate(dataset, SNAPSHOT)
    (SNAPSHOT / "catalog.json").write_text(json.dumps(dataset, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (SNAPSHOT / "source_manifest.json").write_text(json.dumps(sources, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = {"admission_year": 2026, "collected_on": dataset["collected_on"], "source_count": len(sources),
              "pdf_count": sum(s["file"].endswith(".pdf") for s in sources),
              "rule_count": len(rules), "by_university": {}}
    for uni in UNIVERSITIES:
        report["by_university"][uni["id"]] = dict(Counter(r["category"] for r in rules if r["university_id"] == uni["id"]))
    (SNAPSHOT / "coverage.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    from .mipt_programs import build as build_programs
    build_programs(SNAPSHOT)
    if (SNAPSHOT / "organization/catalog.json").exists():
        from .organization_build import Builder
        Builder().build()
    print(json.dumps(Counter(rule["university_id"] for rule in rules), ensure_ascii=False))
    return dataset


if __name__ == "__main__":
    build()
