import json
from pathlib import Path
import sys
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import build_opener, ProxyHandler

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from catalog import Catalog, explicit_codes
from server import make_handler


class WebCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = Catalog()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(cls.catalog))
        cls.worker = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.worker.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"
        # Keep loopback tests independent of system HTTP proxy settings.
        cls.http = build_opener(ProxyHandler({}))

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.worker.join()

    def test_all_rules_and_links_preserved(self):
        c = self.catalog
        self.assertEqual(len(c.rules), 7891)
        self.assertEqual(set(c.universities), {"hse", "itmo", "bmstu", "mipt", "mephi", "mai", "msal"})
        for r in c.rules:
            self.assertIn(r["olympiad_id"], c.olympiads)
            self.assertTrue(r["program_ids"])
            for pid in r["program_ids"]:
                self.assertIn(pid, c.programs)
            self.assertTrue((c.path.parent / c.sources[r["source_id"]]["file"]).is_file())

    def test_exclusions_are_never_positive_field_matches(self):
        for scope in ("все, кроме 41.03.05", "все, за исключением 45.03.02", "Все НП/С, кроме 38.03.00", "45.03.02 (платная основа)", "41.03.05 / все, кроме 41.03.05"):
            self.assertEqual(explicit_codes(scope), [])
        self.assertEqual(explicit_codes("Для направлений: 01.03.02, 09.03.04"), ["01.03.02", "09.03.04"])
        c = self.catalog
        for r in c.rules:
            if r["university_id"] in {"mai", "mephi"} and any(s in r["values"].get("program_scope", "").lower() for s in ("кроме", "исключ")):
                self.assertEqual(r["field_ids"], [])
                self.assertTrue(all(c.programs[p]["kind"] == "group" for p in r["program_ids"]))

    def test_hse_vsosh_and_rsosh_share_known_program(self):
        c = self.catalog
        programs = [p for p in c.programs.values() if p["university_id"] == "hse" and p["name"] == "Математика"]
        self.assertEqual(len(programs), 1)
        p = programs[0]
        self.assertEqual(p["field_id"], "01.03.01")
        rows = c.query({"program": [p["id"]], "limit": ["100"]})["items"]
        self.assertEqual({r["category"] for r in rows}, {"vsosh", "rsosh"})
        self.assertEqual(sum(p["kind"] == "program" and p["university_id"] == "hse" for p in c.programs.values()), 79)
        self.assertEqual(sum(p["kind"] == "program" and p["university_id"] == "hse" and p["rule_count"] > 0 for p in c.programs.values()), 67)
        games = [p for p in c.programs.values() if p["name"] == "Разработка игр и цифровых продуктов" and p["kind"] == "program"]
        self.assertEqual({p["field_id"] for p in games}, {"09.03.04", "54.03.01"})
        for p in games:
            for r in c.query({"program": [p["id"]], "limit": ["100"]})["items"]:
                self.assertEqual(r["values"].get("field_codes"), p["field_id"])

    def test_filters_and_pagination_keep_conditions(self):
        c = self.catalog
        p = {"university": ["hse"], "benefit": ["bvi"], "q": ["высшая проба"], "limit": ["1"]}
        result = c.query(p)
        self.assertGreater(result["total"], 1)
        first = result["items"][0]
        second = c.query({**p, "offset": ["1"]})["items"][0]
        self.assertNotEqual(first["id"], second["id"])
        self.assertEqual(first["university_id"], "hse")
        self.assertIn("bvi", first["benefit_types"])
        self.assertEqual(first["values"], c.by_id[first["id"]]["values"])
        self.assertEqual(first["conditions"], c.by_id[first["id"]]["conditions"])
        self.assertNotIn("search", first)

    def test_mipt_programs_are_present_and_school_links_are_qualified(self):
        c = self.catalog
        ps = [p for p in c.programs.values() if p["university_id"] == "mipt" and p["kind"] == "program"]
        self.assertEqual(len(ps), 30)
        self.assertEqual(len({p["field_id"] for p in ps}), 10)
        self.assertEqual(c.universities["mipt"]["program_count"], 30)
        self.assertEqual(c.universities["mipt"]["field_count"], 10)
        cs = next(p for p in ps if p["name"] == "Computer Science/Информатика")
        self.assertEqual(cs["competition_group"], "Computer Science for foreign citizens")
        for p in ps:
            self.assertEqual(p["rule_relation"], "school_conditions")
            self.assertEqual(p["source_id"], "mipt_places")
            self.assertIn("mipt", c.fields[p["field_id"]]["university_ids"])
            rows = c.query({"program": [p["id"]], "limit": ["100"]})["items"]
            self.assertGreater(len(rows), 0)
            for r in rows:
                self.assertEqual(r["values"]["program_scope"], p["rule_scope"])
                self.assertNotIn(p["id"], r["program_ids"])
                self.assertIn(p["id"], r["related_program_ids"])
                self.assertEqual(r["values"], c.by_id[r["id"]]["values"])

    def test_mipt_source_rowspans_and_repeated_quota_rows(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "data_loader"))
        from admissions.mipt_programs import parse
        c = self.catalog
        source = json.loads((c.path.parent / "sources/mipt_places.json").read_text(encoding="utf-8"))
        parsed = parse(source)
        saved = json.loads((c.path.parent / "programs.json").read_text(encoding="utf-8"))["programs"]
        self.assertEqual(parsed, saved)
        p = next(p for p in parsed if p["name"] == "Радиотехника и компьютерные технологии")
        self.assertEqual(p["field_id"], "03.03.01")
        self.assertEqual(len(p["source_rows"]), 4)
        p = next(p for p in parsed if p["name"] == "AI360: Передовые методы искусственного интеллекта")
        self.assertEqual(p["competition_group"], "Прикладная математика и информатика")
        self.assertEqual(p["school"], "ФПМИ")

    def test_organization_graph_and_source_integrity(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "data_loader"))
        from admissions.organization import validate
        self.assertEqual(validate(), {"universities": 7, "units": 206, "programs": 378})
        c = self.catalog
        self.assertEqual({k: u["unit_count"] for k, u in c.universities.items()},
                         {"hse": 21, "itmo": 17, "bmstu": 12, "mipt": 12, "mephi": 9, "mai": 12, "msal": 8})
        for u in c.units.values():
            self.assertGreater(u["program_count"], 0)
            for pid in u["program_ids"]:
                p = c.programs[pid]
                self.assertEqual(u["university_id"], p["university_id"])
                self.assertIn(u["id"], p["unit_ids"] + p["department_ids"])

    def test_multiple_units_and_faculty_filter(self):
        c = self.catalog
        p = next(p for p in c.programs.values() if p["university_id"] == "bmstu" and p["field_id"] == "09.03.01" and p["unit_ids"])
        self.assertEqual(set(p["unit_ids"]), {"bmstu-iu", "bmstu-rk"})
        self.assertEqual({c.units[x]["code"] for x in p["department_ids"]}, {"ИУ5", "ИУ6", "РК6"})
        result = c.query({"unit": ["bmstu-rk"], "field": ["09.03.01"], "benefit": ["bvi"], "limit": ["100"]})
        self.assertGreater(result["total"], 0)
        for r in result["items"]:
            self.assertIn("bmstu-rk", r["unit_ids"])
            self.assertIn("09.03.01", r["field_ids"])
            self.assertIn("bvi", r["benefit_types"])
        self.assertEqual(c.query({"unit": ["bmstu-rk"], "university": ["hse"]})["total"], 0)
        hse = c.query({"unit": ["hse-269069"], "field": ["01.03.01"], "category": ["vsosh"]})
        self.assertGreater(hse["total"], 0)

    def test_mipt_separate_biological_schools_and_msal_tracks(self):
        c = self.catalog
        ps = [p for p in c.programs.values() if p.get("school") == "ФБМФ, ВШБИ"]
        self.assertGreater(len(ps), 1)
        for p in ps:
            self.assertEqual(len(p["unit_ids"]), 1)
            code = c.units[p["unit_ids"][0]]["code"]
            self.assertIn(code, p["name"])
            self.assertEqual(p["rule_scope"], "ФБМФ/ ВШБИ")
        p = next(p for p in c.programs.values() if p["university_id"] == "msal" and p["name"] == "Бизнес-юрист")
        self.assertEqual(p["field_id"], "40.03.01")
        self.assertEqual(p["tracks"], ["Юрист в сфере бизнес-права", "Юрист в сфере банкротства"])
        self.assertEqual(c.units[p["unit_ids"][0]]["name"], "Институт бизнес-права")

    def test_programs_without_rules_remain_visible_and_exclusions_remain_separate(self):
        c = self.catalog
        p = next(p for p in c.programs.values() if p["unit_ids"] and not p["rule_count"])
        self.assertIn(p["university_id"], p["university_ids"])
        self.assertIn(p["university_id"], c.fields[p["field_id"]]["university_ids"])
        for r in c.rules:
            if not r["field_ids"] and r["university_id"] not in ("mipt",):
                self.assertEqual(r["related_program_ids"], [])

    def test_university_benefit_pairs_come_from_same_rules(self):
        c = self.catalog
        for o in c.olympiads.values():
            for uid, bs in o["university_benefits"].items():
                actual = {b for r in c.rules if r["olympiad_id"] == o["id"] and r["university_id"] == uid for b in r["benefit_types"]}
                self.assertEqual(set(bs), actual)

    def test_http_deep_links_and_sources(self):
        c = self.catalog
        for path in ("/", "/universities/hse", "/units/bmstu-iu", "/fields/09.03.01?unit=bmstu-iu", "/olympiads/" + next(iter(c.olympiads)), "/fields/01.03.01", "/programs/" + next(iter(c.programs)), "/favorites"):
            with self.http.open(self.base + path, timeout=10) as response:
                self.assertEqual(response.status, 200)
                self.assertIn(b'/app.js', response.read())
        with self.http.open(self.base + "/api/catalog", timeout=10) as response:
            data = json.load(response)
            self.assertEqual(data["rule_count"], 7891)
        source = next(s for s in c.sources.values() if s["file"].endswith(".pdf"))
        with self.http.open(self.base + "/sources/" + source["id"], timeout=10) as response:
            self.assertEqual(response.headers["Content-Type"], "application/pdf")
            self.assertTrue(response.read(5).startswith(b'%PDF'))

    def test_http_limits_and_file_boundaries(self):
        for path, status in (("/api/rules?offset=broken", 400), ("/sources/..%2F..%2F.git%2Fconfig", 404), ("/.git/config", 404), ("/unknown", 404)):
            with self.assertRaises(HTTPError) as error:
                self.http.open(self.base + path, timeout=10)
            self.assertEqual(error.exception.code, status)
        with self.http.open(self.base + "/api/rules?limit=10000", timeout=10) as response:
            data = json.load(response)
            self.assertEqual(len(data["items"]), 100)


if __name__ == "__main__":
    unittest.main()
