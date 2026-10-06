#!/usr/bin/env python3
"""Independent caption probe. Network/parse failures are unknown, never absent."""
import argparse
import json
import re
import subprocess
import time
from pathlib import Path

UA = 'Mozilla/5.0'

def assess(html):
    decoder = json.JSONDecoder()
    markers = re.finditer(r'(?:var\s+)?ytInitialPlayerResponse\s*=\s*', html)
    response = None
    for marker in markers:
        try:
            response, _ = decoder.raw_decode(html[marker.end():])
            break
        except (ValueError, TypeError):
            continue
    if not isinstance(response, dict):
        return {'status':'unknown','reason':'player response missing or unparseable','tracks':[]}
    if response.get('playabilityStatus', {}).get('status') != 'OK':
        return {'status':'unknown','reason':'not confirmed playable','tracks':[]}
    track_info = response.get('captions', {}).get('playerCaptionsTracklistRenderer', {})
    tracks = track_info.get('captionTracks', [])
    if not isinstance(tracks, list):
        return {'status':'unknown','reason':'invalid caption track schema','tracks':[]}
    if any(not isinstance(t, dict) or not t.get('languageCode') for t in tracks):
        return {'status':'unknown','reason':'invalid track entry','tracks':[]}
    return {'status':'present' if tracks else 'absent', 'reason':'playable player response',
            'tracks':[{'language':t['languageCode'],'kind':'auto' if t.get('kind')=='asr' else 'manual'} for t in tracks]}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--dir',required=True)
    ap.add_argument('--sleep',type=float,default=1.5)
    a=ap.parse_args()
    if a.sleep<0: ap.error('--sleep must be nonnegative')
    root=Path(a.dir).expanduser()
    rows=[]
    for path in sorted(root.glob('*.info.json')):
        data=json.loads(path.read_text(encoding='utf-8'))
        if data.get('_type')=='playlist': continue
        vid=str(data.get('id',''))
        if not re.fullmatch(r'[A-Za-z0-9_-]{11}',vid):
            row={'status':'unknown','reason':'missing/invalid YouTube ID','tracks':[]}
        else:
            try:
                result=subprocess.run(['curl','--fail','--silent','--show-error','--max-time','30',
                    '-A',UA,f'https://www.youtube.com/watch?v={vid}'],capture_output=True,text=True,timeout=35)
                row=assess(result.stdout) if result.returncode==0 else {'status':'unknown','reason':'HTTP/network request failed','tracks':[]}
            except (OSError,subprocess.TimeoutExpired):
                row={'status':'unknown','reason':'request unavailable or timed out','tracks':[]}
        row.update(video_id=vid,title=data.get('title',''),date=data.get('upload_date',''))
        rows.append(row)
        print(vid, row['status'],row['reason'])
        time.sleep(a.sleep)
    if not rows: raise SystemExit('No video metadata found; nothing was verified.')
    (root/'_caption_audit.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    counts={state:sum(x['status']==state for x in rows) for state in ('present','absent','unknown')}
    print(json.dumps(counts,ensure_ascii=False))
    if counts['unknown']: raise SystemExit(1)

if __name__=='__main__': main()
