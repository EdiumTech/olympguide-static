import copy
from contextlib import closing
import json
import re
import sqlite3
import tempfile
import unittest
from pathlib import Path

from admissions.loader import load_sqlite, postgres_sql, validate
from admissions.paths import SNAPSHOT


class CatalogueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = json.loads((SNAPSHOT / "catalog.json").read_text(encoding="utf-8"))
        cls.rules = cls.dataset["rules"]

    def matching(self, university, **values):
        return [r for r in self.rules if r["university_id"] == university
                and all(r["values"].get(k) == v for k, v in values.items())]

    def test_all_sources_and_universities(self):
        self.assertEqual(len(validate(self.dataset, SNAPSHOT)), 7)
        for uni in self.dataset["universities"]:
            self.assertTrue(any(r["university_id"] == uni["id"] and r["category"] == "rsosh" for r in self.rules))
            self.assertTrue(any(r["university_id"] == uni["id"] and r["category"] == "vsosh" for r in self.rules))

    def test_hse_merged_name_at_bottom_of_page(self):
        found = self.matching("hse", olympiad_name="Московская олимпиада школьников", olympiad_profile="математика", program_scope="Математика")
        bvi = [r for r in found if r["benefit_types"] == ["bvi"]]
        self.assertEqual({r["values"]["grades"] for r in bvi}, {"10 класс", "11 класс"})
        self.assertTrue(all(r["values"]["confirmation_score"] == "75 и более" for r in bvi))

    def test_mai_all_numbered_rows_and_split_nto_profile(self):
        found = [r for r in self.rules if r["university_id"] == "mai" and r["category"] == "rsosh"]
        self.assertEqual({int(r["values"]["document_number"]) for r in found}, set(range(1, 218)))
        self.assertEqual(len(found), 217)
        worlds = next(r for r in found if r["values"]["document_number"] == "9")
        self.assertIn("архитектуре", worlds["values"]["olympiad_profile"])
        self.assertIn("исключением", worlds["values"]["program_scope"])
        self.assertIn("45.03.02", worlds["values"]["program_scope"])
        data = next(r for r in found if r["values"]["document_number"] == "8")
        self.assertIn("машинное обучение", data["values"]["olympiad_profile"])

    def test_msal_grade_specific_rights(self):
        found = self.matching("msal", olympiad_name="Кутафинская олимпиада школьников по праву")
        self.assertEqual(len(found), 2)
        grades = {r["values"]["grades"]: r["benefit_types"] for r in found}
        self.assertEqual(grades["10"], ["100_points"])
        self.assertEqual(grades["11"], ["bvi", "100_points"])

    def test_mephi_grade_eight_and_empty_bvi(self):
        found = self.matching("mephi", olympiad_name="Отраслевая олимпиада школьников «Газпром»", olympiad_profile="инженерное дело")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["benefit_types"], ["100_points"])
        self.assertEqual(found[0]["values"]["grades"], "8, 9, 10, 11")

    def test_mipt_preserves_conditional_thresholds_and_school(self):
        found = [r for r in self.rules if r["university_id"] == "mipt" and "85 баллов" in r["values"]["benefit"]]
        self.assertTrue(found)
        self.assertTrue(all(r["values"]["program_scope"] for r in found))
        self.assertTrue(any(r["values"]["program_scope"] == "ФПМИ" for r in found))

    def test_bmstu_year_boundary_on_same_page(self):
        page = [r for r in self.rules if r["source_id"] == "bmstu_190" and r["location"]["page"] == 66]
        self.assertEqual({r["values"]["olympiad_year"] for r in page if r["location"]["table"] == 1}, {"2025/26"})
        self.assertEqual({r["values"]["olympiad_year"] for r in page if r["location"]["table"] == 2}, {"2024/25"})
        self.assertFalse(any("Профиль олимпиады" in r["values"]["olympiad_profile"] for r in page))

    def test_bmstu_explicit_names_agree_with_reconstructed_names(self):
        normalize = lambda s: re.sub(r"[^а-яa-z0-9]", "", s.lower().replace("ё", "е").replace("класса", "класс"))
        for source_id in ("bmstu_190", "bmstu_315"):
            source = json.loads((SNAPSHOT / "sources" / (source_id + ".json")).read_text(encoding="utf-8"))
            for rule in (r for r in self.rules if r["source_id"] == source_id):
                loc = rule["location"]
                raw = source["pages"][loc["page"] - 1]["tables"][loc["table"] - 1][loc["row"] - 1]
                if raw[1]:
                    self.assertIn(normalize(raw[1]), normalize(rule["values"]["olympiad_name"]), str(loc))

    def test_itmo_page_continuation_does_not_include_letterhead(self):
        found = [r for r in self.matching("itmo", olympiad_profile="Информатика") if r["category"] == "vsosh"]
        self.assertEqual(len(found), 1)
        self.assertIn("09.03.01", found[0]["values"]["program_scope"])
        self.assertIn("45.03.04", found[0]["values"]["program_scope"])
        for rule in self.rules:
            self.assertNotIn("ерситет ИТМО»,", rule["values"]["olympiad_profile"])
            self.assertNotIn("овательное учреждение", rule["values"]["olympiad_profile"])

    def test_sqlite_roundtrip_idempotence_and_validation_before_write(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "admissions.db"
            counts = load_sqlite(self.dataset, path)
            self.assertEqual(load_sqlite(self.dataset, path), counts)
            with closing(sqlite3.connect(path)) as conn:
                actual = {row[0]: json.loads(row[1]) for row in conn.execute("SELECT id,payload FROM admission_rule")}
                self.assertEqual(actual, {r["id"]: r for r in self.rules})
                conn.execute("INSERT INTO admission_university VALUES (2025, 'historical', '{}')")
                conn.commit()
            bad = copy.deepcopy(self.dataset)
            bad["rules"][0]["source_id"] = "unknown"
            with self.assertRaises(ValueError):
                load_sqlite(bad, path)
            load_sqlite(self.dataset, path)
            with closing(sqlite3.connect(path)) as conn:
                self.assertEqual(conn.execute("SELECT count(*) FROM admission_rule").fetchone()[0], len(self.rules))
                self.assertEqual(conn.execute("SELECT count(*) FROM admission_university WHERE admission_year=2025").fetchone()[0], 1)

    def test_postgres_export_quotes_values_and_is_transactional(self):
        dataset = copy.deepcopy(self.dataset)
        dataset["universities"][0]["name"] = "O'Brien \\ path"
        sql = postgres_sql(dataset)
        self.assertTrue(sql.startswith("BEGIN;"))
        self.assertTrue(sql.rstrip().endswith("COMMIT;"))
        self.assertIn("O''Brien", sql)
        self.assertIn("SET LOCAL standard_conforming_strings = on", sql)
        self.assertNotIn("DELETE FROM benefit", sql)


if __name__ == "__main__":
    unittest.main()
