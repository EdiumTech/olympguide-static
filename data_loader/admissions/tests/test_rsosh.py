import copy
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from data_loader.admissions.rsosh import load, validate, parse_docx, export_sql, MANIFEST, SNAPSHOT
from data_loader.admissions.download import install, read_manifest


class RegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load()

    def test_complete_official_profile_table(self):
        data = self.data
        self.assertEqual(validate(data)['profiles'], 303)
        self.assertEqual(data['olympiads'], parse_docx(SNAPSHOT / 'sources/project.docx'))
        rows = [e for e in data['olympiads'] if e['registry_number'] == 5]
        # The obsolete composite NTO profile is not copied to the new season.
        self.assertTrue(any(e['profile'] == 'беспилотные авиационные системы' and e['level'] == 3 for e in rows))
        self.assertFalse(any(e['profile'].startswith('беспилотный транспорт:') for e in rows))
        self.assertEqual(len(data['contacts']), 7)

    def test_missing_level_profile_duplicates_and_wrong_season_fail(self):
        mutations = [lambda d: d['olympiads'][0].update(level=0),
                     lambda d: d['olympiads'][0].update(profile=''),
                     lambda d: d['olympiads'].append(d['olympiads'][0]),
                     lambda d: d.update(academic_year='2027/2028'),
                     lambda d: d.update(status='approved')]
        for mutate in mutations:
            data = copy.deepcopy(self.data)
            mutate(data)
            with self.assertRaises(ValueError):
                validate(data)

    def test_manifest_does_not_confuse_academic_and_admission_years(self):
        manifest = read_manifest(MANIFEST)
        self.assertNotIn('admission_year', manifest)
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / 'manifest.json'
            bad.write_text(json.dumps(dict(manifest, admission_year=2026)))
            with self.assertRaises(ValueError):
                read_manifest(bad)

    def test_archive_install_and_tamper_detection(self):
        manifest = read_manifest(MANIFEST)
        archive = SNAPSHOT.parent / (manifest['release_tag'] + '.zip')
        if not archive.exists():
            self.skipTest('Run rsosh package for the local archive installation test')
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'registry'
            install(manifest_path=MANIFEST, target=target, archive=archive)
            self.assertEqual(load(target), self.data)
            (target / 'catalog.json').write_text('{}')
            with self.assertRaises(ValueError):
                install(manifest_path=MANIFEST, target=target, archive=archive)

    def test_idempotent_import_keeps_ids_favourites_and_calendar_marks(self):
        dsn, psql = os.getenv('OLYMPGUIDE_TEST_DSN'), os.getenv('PSQL')
        if not dsn or not psql:
            self.skipTest('Set OLYMPGUIDE_TEST_DSN and PSQL for a migrated disposable database')
        statement = export_sql(self.data).removeprefix('BEGIN;').removesuffix('COMMIT;\n')
        sql = '''BEGIN;
          CREATE TEMP TABLE registry_test_user AS
            WITH u AS (INSERT INTO olympguide."user"(email,password_hash)
              VALUES('registry-test-'||txid_current()||'@test.invalid','test-only') RETURNING user_id) SELECT * FROM u;
          INSERT INTO olympguide.liked_olympiads(user_id,olympiad_id)
            SELECT user_id,olympiad_id FROM registry_test_user CROSS JOIN olympguide.olympiad
            WHERE academic_year='2026/2027' ORDER BY olympiad_id LIMIT 1;
          INSERT INTO olympguide.calendar_plan(user_id,event_id,status,note,seen_revision)
            SELECT user_id,id,'registered','Keep my participation note',revision
            FROM registry_test_user CROSS JOIN olympguide.calendar_event ORDER BY id LIMIT 1;
          CREATE TEMP TABLE likes_before AS SELECT * FROM olympguide.liked_olympiads;
          CREATE TEMP TABLE registry_before AS SELECT catalog_key,olympiad_id FROM olympguide.olympiad;
          CREATE TEMP TABLE plan_before AS SELECT * FROM olympguide.calendar_plan;
        ''' + statement + statement + '''
          DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM registry_before b LEFT JOIN olympguide.olympiad o USING(catalog_key)
              WHERE o.olympiad_id IS DISTINCT FROM b.olympiad_id AND b.catalog_key IS NOT NULL)
              THEN RAISE EXCEPTION 'An existing olympiad identity changed'; END IF;
            IF (SELECT count(*) FROM olympguide.olympiad WHERE registry_active AND academic_year='2026/2027') <> 303
              THEN RAISE EXCEPTION 'Import duplicates or missing profiles'; END IF;
            IF EXISTS ((SELECT * FROM plan_before EXCEPT SELECT * FROM olympguide.calendar_plan)
              UNION ALL (SELECT * FROM olympguide.calendar_plan EXCEPT SELECT * FROM plan_before))
              THEN RAISE EXCEPTION 'Personal calendar marks changed'; END IF;
            IF EXISTS ((SELECT * FROM likes_before EXCEPT SELECT * FROM olympguide.liked_olympiads)
              UNION ALL (SELECT * FROM olympguide.liked_olympiads EXCEPT SELECT * FROM likes_before))
              THEN RAISE EXCEPTION 'Favourites changed'; END IF;
            IF EXISTS (SELECT 1 FROM olympguide.admission_rule ar JOIN olympguide.olympiad o USING(olympiad_id)
              WHERE o.academic_year='2026/2027') THEN RAISE EXCEPTION 'Admission rules carried forward'; END IF;
          END $$;
          ROLLBACK;
        '''
        result = subprocess.run([psql, dsn, '-X', '-q', '-v', 'ON_ERROR_STOP=1'],
                                input=sql, text=True, encoding='utf-8', capture_output=True,
                                env=dict(os.environ, PGCLIENTENCODING='UTF8'))
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
