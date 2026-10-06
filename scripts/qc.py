#!/usr/bin/env python3
"""Diagnostic subtitle checks, not a speech-accuracy or coverage measurement."""
import argparse
import collections
import json
import re
from pathlib import Path
from subtitle_utils import read_cues

def longest_run(seq, pred):
    run=best=0
    for value in seq:
        run=run+1 if pred(value) else 0
        best=max(best,run)
    return best

def is_numeric_seg(text):
    value=re.sub(r'[\s,，.。、%－\-—/]','',text)
    return bool(value) and len(re.findall(r'\d',value))/len(value)>=0.75

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--dir',required=True)
    ap.add_argument('--glob',default=None,help='Default: both SRT and VTT')
    ap.add_argument('--known')
    ap.add_argument('--min-cov',type=float,default=.95,help='End alignment threshold; NOT speech coverage')
    ap.add_argument('--min-dens',type=float,default=150,help='Chinese speech heuristic, chars/min')
    a=ap.parse_args()
    root=Path(a.dir).expanduser()
    paths=sorted(root.glob(a.glob)) if a.glob else sorted(set(root.glob('*.srt'))|set(root.glob('*.vtt')))
    rows=[]
    issues=[]
    if not paths: issues.append('No subtitle files found')
    alltext=[]
    for path in paths:
        stem=re.sub(r'\.[A-Za-z0-9-]+\.(?:srt|vtt)$','',path.name)
        if stem==path.name: stem=path.stem
        errors=[]
        duration=0
        try:
            meta=json.loads((root/(stem+'.info.json')).read_text(encoding='utf-8'))
            duration=float(meta.get('duration') or 0)
            if duration<=0: errors.append('Missing/invalid duration metadata')
        except (OSError,ValueError,TypeError): errors.append('Missing/invalid metadata')
        try: cues=read_cues(path)
        except (OSError,ValueError) as error:
            cues=[]
            errors.append(str(error))
        if not cues: errors.append('No readable subtitle cues')
        texts=[c[2] for c in cues]
        alltext.extend(texts)
        end=max((c[1] for c in cues),default=0)
        align=end/duration if duration>0 else None
        density=sum(len(re.sub(r'\s','',t)) for t in texts)/(duration/60) if duration>0 else None
        if align is not None and align<a.min_cov: errors.append('Subtitle end does not reach expected duration')
        if align is not None and align>1.05: errors.append('Subtitle end exceeds duration metadata')
        if any(cues[i][0]<cues[i-1][0] for i in range(1,len(cues))): errors.append('Out-of-order cues')
        dup=longest_run(range(1,len(texts)),lambda i:texts[i]==texts[i-1])
        if dup>=3: errors.append('Four or more repeated consecutive cues')
        numeric=longest_run(texts,is_numeric_seg)
        if numeric>=6: errors.append('Six or more consecutive mostly numeric cues (review context)')
        for text in texts:
            value=re.sub(r'\s','',text)
            if len(value)>=40 and any(value.count(value[:n])>=8 and value.count(value[:n])*n>len(value)*.7 for n in range(1,7)):
                errors.append('Within-cue repetition'); break
        if density is not None and density<a.min_dens: errors.append('Low content density (Chinese speech heuristic)')
        row={'file':path.name,'duration_seconds':duration,'subtitle_end_seconds':end,
             'end_alignment_ratio':align,'chars_per_minute':density,'problems':errors}
        rows.append(row)
        issues.extend(path.name+': '+x for x in errors)
    known=set()
    if a.known: known=set(Path(a.known).expanduser().read_text(encoding='utf-8').split())
    counts=collections.Counter(re.findall(r'[A-Za-z][A-Za-z0-9.]{1,14}','\n'.join(alltext)))
    suspects=[{'term':term,'count':count} for term,count in counts.most_common() if count>=3 and term not in known]
    report={'status':'review-required' if issues else 'no-diagnostic-alerts','scope':'heuristic checks only; not transcript accuracy',
            'files':rows,'problems':issues,'english_terms_for_review':suspects}
    if root.is_dir(): (root/'qc-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if issues: raise SystemExit(1)

if __name__=='__main__': main()
