#!/usr/bin/env python3
"""Validate source identity, dates and timestamp references; not semantic support."""
import argparse
import collections
import datetime
import json
import re
from pathlib import Path

def field(text,key):
    if not text.startswith('---\n'): return None
    head=text.split('---',2)[1]
    match=re.search(r'^'+re.escape(key)+r':\s*(.*?)\s*$',head,re.M)
    if not match: return None
    value=match.group(1).strip()
    if value.startswith('"'):
        try: return str(json.loads(value))
        except ValueError: return None
    return value.strip("'")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--out',required=True)
    ap.add_argument('--synopsis')
    ap.add_argument('--per-ep-dir',default='逐期')
    a=ap.parse_args()
    root=Path(a.out).expanduser()
    paths=sorted((root/a.per_ep_dir).glob('*.md'))
    fail=[]
    if not paths: raise SystemExit('No episode notes found')
    sources={}
    dates=collections.defaultdict(list)
    for path in paths:
        text=path.read_text(encoding='utf-8')
        vid=field(text,'video_id')
        date=field(text,'date')
        try: datetime.date.fromisoformat(date)
        except (ValueError,TypeError): fail.append(path.name+': missing/invalid date')
        match=re.match(r'(\d{8})',path.name)
        if not match or not date or match.group(1)!=date.replace('-',''):
            fail.append(path.name+': filename/frontmatter date mismatch')
        key=vid or path.name
        if key in sources: fail.append('Duplicate video ID: '+key)
        sources[key]=path
        if date: dates[date.replace('-','')].append(key)
        if not field(text,'url'): fail.append(path.name+': missing source URL')
        before,sep,points=text.partition('## 方法论要点')
        if not sep or not points.strip(): fail.append(path.name+': missing methodology section')
        anchors=set(re.findall(r'\*\*\[(\d{2}:\d{2}:\d{2})\]\*\*',before))
        pointstamps=re.findall(r'\[(\d{2}:\d{2}:\d{2})\]',points)
        if not anchors: fail.append(path.name+': no transcript anchors')
        if not pointstamps and '未提取到可复用规则' not in points:
            fail.append(path.name+': methodology has no timestamp references')
        for line in points.splitlines():
            if re.match(r'\s*[-*]\s+',line) and not re.search(r'\[\d{2}:\d{2}:\d{2}\]',line):
                fail.append(path.name+': methodology bullet lacks timestamp')
        for stamp in pointstamps:
            if stamp not in anchors: fail.append(path.name+': unknown transcript anchor '+stamp)
    synopsis=root/a.synopsis if a.synopsis else None
    if not synopsis:
        candidates=sorted(root.glob('*总纲*.md'))
        if len(candidates)!=1: raise SystemExit('Provide --synopsis when synopsis is missing or ambiguous')
        synopsis=candidates[0]
    text=synopsis.read_text(encoding='utf-8')
    cited=set()
    ids=re.findall(r'\[video:([^\]\s]+)\]',text)
    legacy=re.findall(r'\[(\d{8}|\d{6})\]',text)
    if not ids and not legacy: fail.append('No source references found')
    for vid in ids:
        if vid not in sources: fail.append('Dead video reference: '+vid)
        else: cited.add(vid)
    for date in legacy:
        date=('20'+date) if len(date)==6 else date
        matches=dates.get(date,[])
        if len(matches)!=1: fail.append('Dead/ambiguous date reference: '+date+'; use [video:ID]')
        else: cited.add(matches[0])
    for key in set(sources)-cited: fail.append('Unreferenced episode: '+sources[key].name)
    for error in fail: print('FAIL:',error)
    print(f'Checked {len(paths)} episode notes; {len(cited)} referenced; {len(fail)} structural problems.')
    print('This check does not prove transcription accuracy or semantic support.')
    if fail: raise SystemExit(1)

if __name__=='__main__': main()
