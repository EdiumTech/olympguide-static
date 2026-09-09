"""Collect checksum-bound official tuition and admission-place sources for 2026."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import requests
from lxml import html

ROOT = Path(__file__).parent / 'snapshots/2026-quantities'

def clean(x):
    if hasattr(x, 'text_content'): x = x.text_content()
    return ' '.join(str(x).replace('\xa0',' ').split())

def fetch(key, university, url, *, ca_bundle=True):
    assert re.fullmatch('[a-z0-9_]+', key)
    directory=ROOT/'sources';directory.mkdir(parents=True,exist_ok=True)
    response=requests.get(url,timeout=45,verify=ca_bundle,headers={'User-Agent':'OlympGuide/1.0 (admissions catalogue)'})
    response.raise_for_status()
    body=response.content
    suffix='.pdf' if body.startswith(b'%PDF') else '.json' if 'json' in response.headers.get('Content-Type','') else '.html'
    filename=key+suffix
    (directory/filename).write_bytes(body)
    meta=dict(id=key,university=university,url=url,resolved_url=response.url,file='sources/'+filename,
              sha256=hashlib.sha256(body).hexdigest(),retrieved_at=datetime.now(timezone.utc).isoformat())
    (directory/(key+'.meta.json')).write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return meta

def read(key):
    meta=json.loads((ROOT/'sources'/(key+'.meta.json')).read_text(encoding='utf-8'))
    body=(ROOT/meta['file']).read_bytes()
    assert hashlib.sha256(body).hexdigest()==meta['sha256']
    return body.decode('utf-8-sig')

def page(key): return html.fromstring(read(key))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('key');parser.add_argument('university');parser.add_argument('url')
    a=parser.parse_args();print(json.dumps(fetch(a.key,a.university,a.url)))

if __name__=='__main__':main()
