import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from data_loader.admissions.personal import validate, export_sql, verify_sources
from data_loader.admissions.scholarships import REVIEWED, build


class ScholarshipsTest(unittest.TestCase):
    def data(self):
        sources={s:dict(id=s,url='https://official.example/'+s,sha256='a'*64)
                 for r in REVIEWED for s in r['source_ids']}
        return dict(schema_version=1,admission_year=2026,scholarships=build(sources,{}),events=[],evaluations=[])

    def test_null_amounts_and_historical_year_are_preserved(self):
        data=validate(self.data());rows={s['id']:s for s in data['scholarships']}
        self.assertIsNone(rows['bmstu-bvi']['amount_min'])
        self.assertEqual(rows['mipt-academic-spring']['academic_year'],'2025/2026')
        self.assertEqual(rows['itmo-relocation']['frequency'],'one_time')
        self.assertEqual(rows['itmo-family-platinum']['frequency'],'monthly')

    def test_bad_amounts_and_duplicate_ids_rejected_before_import(self):
        for values in [(0,0),(20000,8000),(None,10000),(-1,1000)]:
            data=self.data(); data['scholarships'][0]['amount_min'],data['scholarships'][0]['amount_max']=values
            with self.assertRaises(ValueError):export_sql(data)
        data=self.data();data['scholarships'].append(copy.deepcopy(data['scholarships'][0]))
        with self.assertRaises(ValueError):validate(data)

    def test_program_scope_does_not_follow_faculty(self):
        sources={s:dict(id=s,url='https://official.example/'+s,sha256='a'*64) for r in REVIEWED for s in r['source_ids']}
        rows=build(sources,{'yes':dict(id='yes',university_id='hse',name='Программная инженерия'),
                           'no':dict(id='no',university_id='hse',name='Другая программа ФКН')})
        self.assertEqual(rows[0]['scope']['program_keys'],['yes'])

    def test_sql_upsert_and_escaping(self):
        data=self.data();data['scholarships'][0]['notes']="O'Brien"
        sql=export_sql(data)
        self.assertIn("O''Brien",sql)
        self.assertIn('ON CONFLICT(id) DO UPDATE',sql)
        self.assertTrue(sql.startswith('BEGIN;'))
        self.assertTrue(sql.endswith('COMMIT;'))

    def test_changed_or_escaping_source_evidence_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sources = root / 'sources'
            sources.mkdir()
            evidence = sources / 'official.html'
            evidence.write_bytes(b'official source')
            meta = sources / 'official.meta.json'
            record = dict(file='sources/official.html', sha256=hashlib.sha256(evidence.read_bytes()).hexdigest())
            meta.write_text(json.dumps(record), encoding='utf-8')
            verify_sources(root)
            evidence.write_bytes(b'changed source')
            with self.assertRaises(ValueError): verify_sources(root)
            record['file'] = '../outside.html'
            meta.write_text(json.dumps(record), encoding='utf-8')
            with self.assertRaises(ValueError): verify_sources(root)


if __name__=='__main__':unittest.main()
