"""Standard-library reader and validator for the pinned tuition/places supplement."""
import json
from pathlib import Path
from .download import install, read_manifest, verify_snapshot

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / 'releases/2026-quantities.json'
SNAPSHOT = ROOT / 'snapshots/2026-quantities'
METRICS = ('budget_places', 'paid_places', 'cost')


def validate(data, programs=None):
    if data.get('schema_version') != 1 or data.get('admission_year') != 2026:
        raise ValueError('Unsupported quantity catalog')
    sources = {s['id']: s for s in data['sources']}
    records = {p['id']: p for p in data['programs']}
    if len(records) != len(data['programs']) or len(sources) != len(data['sources']):
        raise ValueError('Duplicate quantity entity')
    if programs is not None:
        expected = {k: p for k, p in programs.items() if p['kind'] != 'group' and not p.get('aggregate')}
        if records.keys() != expected.keys():
            raise ValueError('Quantity supplement does not match program catalog')
        for key, q in records.items():
            if any(q[k] != expected[key][k] for k in ('university_id', 'field_id', 'name')):
                raise ValueError('Quantity supplement program identity mismatch')
    groups, coverage = {}, {}
    for q in records.values():
        if q['admission_year'] != 2026:
            raise ValueError('Mixed admission years')
        counts = coverage.setdefault(q['university_id'], dict(programs=0, budget_places=0, paid_places=0, cost=0))
        counts['programs'] += 1
        for metric in METRICS:
            value, evidence = q[metric], q['quantity_evidence'].get(metric)
            if value is None:
                if evidence is not None:
                    raise ValueError('Evidence for a missing quantity')
                continue
            upper = 10000000 if metric == 'cost' else 32767
            if type(value) is not int or not 0 <= value <= upper or (metric == 'cost' and not value):
                raise ValueError('Invalid quantity range')
            counts[metric] += 1
            if not evidence or evidence['value'] != value or not evidence['locator']:
                raise ValueError('Missing quantity provenance')
            source = sources[evidence['source_id']]
            if source['university'] != q['university_id'] or evidence['source_url'] != source['url']:
                raise ValueError('Quantity source mismatch')
            if metric != 'cost' and evidence.get('group_id'):
                key = (q['university_id'], metric, evidence['group_id'])
                if groups.setdefault(key, value) != value:
                    raise ValueError('Conflicting counts within a shared group')
        if q['cost_period'] != (q['quantity_evidence']['cost']['period'] if q['cost'] is not None else None):
            raise ValueError('Cost period mismatch')
        if q['cost'] is not None and q['cost_period'] not in ('year', 'semester'):
            raise ValueError('Unknown cost period')
        if q['places_known'] != any(q[k] is not None for k in METRICS[:2]) or q['cost_known'] != (q['cost'] is not None):
            raise ValueError('Known flags do not match quantities')
        if any(q[k] is None for k in METRICS) and not q['quantity_notes']:
            raise ValueError('Unexplained missing quantity')
    if coverage != data['coverage']:
        raise ValueError('Quantity coverage mismatch')
    return coverage


def load(*, target=SNAPSHOT, manifest_path=MANIFEST, programs=None):
    target = Path(target)
    manifest = read_manifest(manifest_path)
    verify_snapshot(target, manifest)
    data = json.loads((target / 'catalog.json').read_text(encoding='utf-8'))
    validate(data, programs)
    return data


def download(*, archive=None, target=SNAPSHOT):
    return install(manifest_path=MANIFEST, target=target, archive=archive)
