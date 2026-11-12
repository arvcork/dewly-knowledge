#!/usr/bin/env python3
"""Rebuild and locally verify Dewly's transport bundle.

This script only packages existing knowledge JSON. The SQLite schema/seed importer
belongs to Dewly.Mod and is deliberately not implemented here.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
PUBLISH = ROOT / 'publish'

def canonical_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')

def digest(value):
    return hashlib.sha256(value).hexdigest()

def read_documents():
    docs=[]
    for file in sorted(DATA.rglob('*.json')):
        if not file.is_file(): continue
        rel=file.relative_to(ROOT).as_posix()
        parsed=json.loads(file.read_text(encoding='utf-8'))
        raw=file.read_bytes()
        docs.append({'path':rel,'sha256':digest(raw),'content':parsed})
    if not docs: raise RuntimeError('No data JSON found in data/')
    if len({d['path'] for d in docs})!=len(docs): raise RuntimeError('Duplicate file paths')
    return docs

def counts(docs):
    facts=Counter()
    for d in docs:
        path=d['path']; j=d['content']; group=path.split('/')[1]
        facts[group+'Files'] += 1
        if group in ('achievement-rules','acquisition-rules','progression-rules') and isinstance(j,dict):
            facts['graphNodes'] += len(j.get('nodes', []))
        if group=='achievement-definitions': facts['sourceAchievementDefinitions'] += len(j.get('entries',[]))
        if group=='content-index': facts['materializedGameplayRecords'] += len(j.get('records',[]))
        if path=='data/daily-tasks/generators.json': facts['dailyTaskGenerators'] = len(j.get('records',[]))
    return dict(sorted(facts.items()))

def build():
    docs=read_documents()
    document_revision=digest(canonical_bytes([{'path':d['path'],'sha256':d['sha256']} for d in docs]))
    source_manifest=next(d['content'] for d in docs if d['path']=='data/manifest.json')
    game_version=source_manifest['gameVersion']['installedBuild']
    expected_content_path=f'data/content-index/{game_version}/manifest.json'
    content_manifest=next((d['content'] for d in docs if d['path']==expected_content_path), None)
    if content_manifest is None:
        raise RuntimeError(f'Missing versioned content manifest: {expected_content_path}')
    bundle={
        'format':'dewly.knowledge.bundle',
        'bundleSchemaVersion':1,
        'knowledgeRevision':document_revision,
        'sourceGameVersion':content_manifest['gameVersion'],
        'sourceGameContentFingerprint':content_manifest['contentFingerprint'],
        'dataSchemaVersion':source_manifest['schemaVersion'],
        'documentCount':len(docs),
        'documents':[{'path':d['path'],'content':d['content']} for d in docs],
    }
    bundle_raw=canonical_bytes(bundle)
    manifest={
        'format':'dewly.knowledge.manifest',
        'manifestSchemaVersion':1,
        'channel':'main',
        'knowledgeRevision':document_revision,
        'sourceGameVersion':content_manifest['gameVersion'],
        'sourceGameContentFingerprint':content_manifest['contentFingerprint'],
        'dataSchemaVersion':source_manifest['schemaVersion'],
        'runtimeAuthority':'Active game and loaded mod content take precedence over this vanilla reference snapshot.',
        'payload':{'path':'publish/knowledge.json','sha256':digest(bundle_raw),'bytes':len(bundle_raw),'encoding':'utf-8','compression':'none'},
        'documentCount':len(docs),
        'counts':counts(docs),
        'files':[{'path':d['path'],'sha256':d['sha256']} for d in docs],
        'compatibilityNote':'A mod must check format version, supported game content and all required condition operators before activating imported knowledge.',
    }
    return bundle_raw, (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2)+'\n').encode('utf8'), manifest

def verify():
    bundle_bytes,manifest_bytes,manifest = build()
    existing_bundle=(PUBLISH/'knowledge.json').read_bytes()
    existing_manifest=(PUBLISH/'manifest.json').read_bytes()
    if bundle_bytes != existing_bundle or manifest_bytes != existing_manifest:
        raise RuntimeError('Published payload is stale. Run: python tools/rebuild_publish.py')
    b=json.loads(existing_bundle)
    m=json.loads(existing_manifest)
    if len(b['documents'])!=b['documentCount'] or b['knowledgeRevision']!=m['knowledgeRevision']:
        raise RuntimeError('Bundle/manifest inconsistent')
    paths={x['path'] for x in b['documents']}
    assert len(paths)==len(b['documents'])
    assert all('data/' == x['path'][:5] for x in b['documents'])
    assert all(x['path'] in paths for x in m['files'])
    print(f"OK: {len(paths)} JSON documents; {m['counts']['graphNodes']} graph nodes; SHA256 {m['payload']['sha256']}")

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--verify', action='store_true', help='Validate published artifacts unchanged')
    args=p.parse_args()
    if args.verify:
        verify()
    else:
        PUBLISH.mkdir(parents=True,exist_ok=True)
        b,m,manifest=build()
        (PUBLISH/'knowledge.json').write_bytes(b)
        (PUBLISH/'manifest.json').write_bytes(m)
        verify()

if __name__=='__main__': main()
