"""Package the rebuilt supplement without adding source documents to Git."""
import hashlib
import json
from pathlib import Path
import zipfile
from .quantities import ROOT
from .quantity_catalog import MANIFEST, validate


def build(tag='quantities-2026-20260908'):
    data = json.loads((ROOT / 'catalog.json').read_text(encoding='utf-8'))
    validate(data)
    paths = {ROOT / 'catalog.json'}
    for meta in (ROOT / 'sources').glob('*.meta.json'):
        paths.add(meta)
        source = json.loads(meta.read_text(encoding='utf-8'))
        body = ROOT / source['file']
        if hashlib.sha256(body.read_bytes()).hexdigest() != source['sha256']:
            raise ValueError('Source checksum mismatch: ' + source['id'])
        paths.add(body)
    output = Path(__file__).resolve().parents[2] / 'tmp/releases'
    output.mkdir(parents=True, exist_ok=True)
    archive = output / ('olympguide-' + tag + '.zip')
    files = []
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for path in sorted(paths):
            name, body = path.relative_to(ROOT).as_posix(), path.read_bytes()
            info = zipfile.ZipInfo(name, date_time=(2026, 9, 8, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            bundle.writestr(info, body)
            files.append(dict(path=name, bytes=len(body), sha256=hashlib.sha256(body).hexdigest()))
    manifest = dict(schema_version=1, admission_year=2026, collected_on='2026-09-08', release_tag=tag,
                    coverage=data['coverage'], archive=dict(
                    url=f'https://github.com/EdiumTech/olympguide-static/releases/download/{tag}/{archive.name}',
                    bytes=archive.stat().st_size, sha256=hashlib.sha256(archive.read_bytes()).hexdigest()), files=files)
    # One entry per line keeps the reviewable manifest compact.
    header = json.dumps({k: v for k, v in manifest.items() if k != 'files'}, ensure_ascii=False, indent=2)[:-2]
    MANIFEST.write_text(header + ',\n  "files": [\n' + ',\n'.join('    ' + json.dumps(f, ensure_ascii=False) for f in files) + '\n  ]\n}\n', encoding='utf-8')
    return archive


if __name__ == '__main__':
    print(build())
