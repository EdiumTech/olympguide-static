"""Build, validate, package and install the personal-admissions supplement.

python -m data_loader.admissions.personal build|package|download|export-sql
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile
from .download import install, read_manifest, verify_snapshot
from .scholarships import build as scholarships

ROOT = Path(__file__).resolve().parent
SNAPSHOT = ROOT / 'snapshots/2026-personal'
MANIFEST = ROOT / 'releases/2026-personal.json'
UNIVERSITIES = {'hse', 'itmo', 'bmstu', 'mipt', 'mephi', 'mai', 'msal'}


def validate(data):
    if data.get('schema_version') != 1 or data.get('admission_year') != 2026:
        raise ValueError('Unsupported personal supplement')
    for collection in ('scholarships', 'events', 'evaluations'):
        rows = data.get(collection, [])
        if len({r['id'] for r in rows}) != len(rows):
            raise ValueError('Duplicate ' + collection + ' identity')
    for row in data['scholarships']:
        if row['university_key'] not in UNIVERSITIES or row['kind'] not in ('scholarship', 'grant', 'prize', 'tuition_discount'):
            raise ValueError('Invalid payment identity/kind')
        if row['frequency'] not in ('monthly', 'one_time', 'semester', 'annual', 'tuition'):
            raise ValueError('Invalid payment frequency')
        lo, hi = row['amount_min'], row['amount_max']
        if (lo is None) != (hi is None) or (lo is not None and
                (type(lo) not in (int, float) or type(hi) not in (int, float) or not 0 < lo <= hi)):
            raise ValueError('Unknown amounts must be null; positive ranges must be ordered')
        if row['academic_year'] is not None and not re.fullmatch(r'20\d\d/20\d\d', row['academic_year']):
            raise ValueError('Invalid academic year')
        if not row['sources'] or any(not s['url'].startswith('https://') or not re.fullmatch('[0-9a-f]{64}',s['sha256']) for s in row['sources']):
            raise ValueError('Missing source evidence')
        if row['scope']['type'] not in ('university', 'campus', 'unit', 'program'):
            raise ValueError('Invalid scope')
        if row['scope']['type'] == 'program' and not row['scope']['program_names']:
            raise ValueError('Explicit programs required for program scope')
    from .calendar_events import validate_event
    for event in data.get("events", []): validate_event(event)
    for e in data.get('evaluations', []):
        if e['admission_year'] != data['admission_year'] or not e['source_payload']['source']['url'].startswith('https://'):
            raise ValueError('Invalid evaluation year/source')
        if e['complete'] and (not e['program_keys'] or not e['requirement']):
            raise ValueError('Complete evaluation requires explicit scope and conditions')
    return data


def verify_sources(target=SNAPSHOT):
    target=Path(target).resolve()
    for meta in (target/'sources').glob('*.meta.json'):
        source=json.loads(meta.read_text(encoding='utf-8'))
        path=(target/source['file']).resolve()
        if not path.is_relative_to(target) or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=source['sha256']:
            raise ValueError('Source evidence checksum mismatch: '+meta.name)


def load(target=SNAPSHOT):
    verify_snapshot(target, read_manifest(MANIFEST))
    return validate(json.loads((Path(target) / 'catalog.json').read_text(encoding='utf-8')))


def build():
    verify_sources()
    for name, directory in [('2026.json','2026'), ('2026-quantities.json','2026-quantities')]:
        verify_snapshot(ROOT/'snapshots'/directory, read_manifest(ROOT/'releases'/name))
    sys.path.insert(0, str(ROOT.parents[1] / 'web'))
    from catalog import Catalog
    catalog = Catalog(personal=False)
    sources = {p.stem.removesuffix('.meta'): json.loads(p.read_text(encoding='utf-8'))
               for p in (SNAPSHOT / 'sources').glob('*.meta.json')}
    data = dict(schema_version=1, admission_year=2026, checked_on='2026-09-08',
                scholarships=scholarships(sources, catalog.programs), events=[], evaluations=[])
    from .calendar_events import build as calendar_events
    data["events"] = calendar_events(sources,catalog)
    data["event_collections"] = ["hse-vp-2026-2027", "itmo-admission-2026"]
    from .eligibility_rules import build as eligibility_rules
    data["evaluations"] = eligibility_rules(catalog)
    validate(data)
    (SNAPSHOT / 'catalog.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    return data


def package():
    verify_sources()
    data = validate(json.loads((SNAPSHOT / 'catalog.json').read_text(encoding='utf-8')))
    tag = 'personal-2026-20260908'
    output = ROOT.parents[1] / 'tmp/releases'
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f'olympguide-{tag}.zip'
    files = []
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as bundle:
        for p in sorted(SNAPSHOT.rglob('*')):
            if not p.is_file(): continue
            body = p.read_bytes(); name = p.relative_to(SNAPSHOT).as_posix()
            bundle.writestr(name, body)
            files.append(dict(path=name, bytes=len(body), sha256=hashlib.sha256(body).hexdigest()))
    manifest = dict(schema_version=1, admission_year=2026, release_tag=tag, checked_on=data['checked_on'],
                    archive=dict(url=f'https://github.com/EdiumTech/olympguide-static/releases/download/{tag}/{archive.name}',
                                 bytes=archive.stat().st_size, sha256=hashlib.sha256(archive.read_bytes()).hexdigest()),
                    files=files)
    manifest['dependencies'] = {name: hashlib.sha256((ROOT/'releases'/name).read_bytes()).hexdigest()
                                for name in ('2026.json','2026-quantities.json')}
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    return archive


def literal(value):
    text = json.dumps(value, ensure_ascii=False, separators=(',', ':')) if not isinstance(value, str) else value
    if '\x00' in text: raise ValueError('NUL in SQL text')
    return "'" + text.replace("'", "''") + "'"


def export_sql(data):
    validate(data)
    sql = ['BEGIN;', 'SET LOCAL standard_conforming_strings=on;', 'SELECT pg_advisory_xact_lock(2026, 7891);', 'SELECT pg_advisory_xact_lock(2026, 7900);']
    for row in data['scholarships']:
        sql.append('INSERT INTO olympguide.scholarship(id,university_key,payload) VALUES (' +
                   ','.join(literal(v) for v in (row['id'], row['university_key'], row)) +
                   ') ON CONFLICT(id) DO UPDATE SET university_key=EXCLUDED.university_key,payload=EXCLUDED.payload;')
    for collection in data.get('event_collections', []):
        ids=[e['id'] for e in data['events'] if e['collection_key']==collection]
        keep=' AND id NOT IN ('+','.join(literal(i) for i in ids)+')' if ids else ''
        sql.append(f"UPDATE olympguide.calendar_event SET active=false,updated_at=now() WHERE collection_key={literal(collection)}{keep};")
    for event in data.get('events', []):
        payload=dict(event)
        payload.pop('revision')
        olymp_keys=','.join(literal(k) for k in event.get('olympiad_keys',[])) or "NULL"
        program_keys=','.join(literal(k) for k in event.get('program_keys',[])) or "NULL"
        program_where=f'p.catalog_key IN ({program_keys})'
        if not event.get('program_keys') and event.get('university_key'):
            program_where=f'u.catalog_key={literal(event["university_key"])}'
        enriched=(literal(payload)+"::jsonb || jsonb_build_object('olympiad_ids',"+
            f"(SELECT COALESCE(jsonb_agg(olympiad_id ORDER BY olympiad_id),'[]'::jsonb) FROM olympguide.olympiad WHERE catalog_key IN ({olymp_keys})),"+
            "'program_ids',"+f"(SELECT COALESCE(jsonb_agg(p.program_id ORDER BY p.program_id),'[]'::jsonb) FROM olympguide.educational_program p JOIN olympguide.university u USING(university_id) WHERE {program_where}))")
        sql.append('INSERT INTO olympguide.calendar_event(id,season,collection_key,revision,payload) VALUES ('+
            ','.join(literal(event[k]) for k in ('id','season','collection_key','revision'))+','+enriched+
            ') ON CONFLICT(id) DO UPDATE SET season=EXCLUDED.season,collection_key=EXCLUDED.collection_key,revision=EXCLUDED.revision,payload=EXCLUDED.payload,active=true,updated_at=now();')
    if 'evaluations' in data:
        sql.append('DELETE FROM olympguide.admission_evaluation WHERE admission_year=2026;')
    for evaluation in data.get('evaluations', []):
        payload={k:v for k,v in evaluation.items() if k!='source_payload'}
        expected=literal(evaluation['source_payload'])
        sql.append('INSERT INTO olympguide.admission_evaluation(id,admission_year,rule_id,payload,source_payload) VALUES ('+
            literal(evaluation['id'])+',2026,'+literal(evaluation['rule_id'])+','+literal(payload)+','+expected+');')
    if data.get('evaluations'):
        sql.append("DO $$ BEGIN IF EXISTS(SELECT 1 FROM olympguide.admission_evaluation e JOIN olympguide.admission_rule r ON r.admission_year=e.admission_year AND r.id=e.rule_id WHERE e.admission_year=2026 AND e.source_payload<>r.payload) THEN RAISE EXCEPTION 'Eligibility source mismatch'; END IF; END $$;")
    from .rsosh import calendar_registry_sql
    sql.append(calendar_registry_sql())
    sql.append('COMMIT;')
    return '\n'.join(sql)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['build', 'package', 'download', 'validate', 'export-sql'])
    p.add_argument('--archive', type=Path)
    p.add_argument('--output', type=Path)
    a = p.parse_args()
    if a.command == 'build': print({k: len(v) for k,v in build().items() if isinstance(v,list)})
    elif a.command == 'package': print(package())
    elif a.command == 'download': print(install(manifest_path=MANIFEST,target=a.output or SNAPSHOT,archive=a.archive))
    elif a.command == 'validate': print('Verified personal supplement:', len(load()['scholarships']), 'payments')
    elif a.command == 'export-sql':
        if not a.output: p.error('--output is required')
        a.output.write_text(export_sql(load()),encoding='utf-8')


if __name__ == '__main__': main()
