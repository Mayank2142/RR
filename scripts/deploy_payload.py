"""Prepare only explicitly allowed source/assets for the Vercel connector."""
from pathlib import Path
import argparse
import base64
import hashlib
import json
ROOT=Path(__file__).resolve().parents[1]
PAYLOAD=ROOT/'tmp'/'vercel-payload.json'
def build():
    files=[ROOT/'vercel.json']
    files += [ROOT/'frontend'/p for p in ['package.json','package-lock.json','index.html','tsconfig.json','vite.config.ts']]
    files += sorted((ROOT/'frontend'/'src').rglob('*'))
    files += [ROOT/'frontend'/'public'/'analysis.json',ROOT/'frontend'/'public'/'SupeRR_Selector_Report.pdf']
    files += [ROOT/'backend'/'app.py',ROOT/'backend'/'requirements.txt',ROOT/'backend'/'data'/'analysis.json']
    manifest=[];uploads={}
    for p in files:
        if not p.is_file():continue
        data=p.read_bytes();sha=hashlib.sha1(data).hexdigest()
        manifest.append({'file':p.relative_to(ROOT).as_posix(),'sha':sha,'size':len(data)})
        uploads.setdefault(sha,{'size':len(data),'data':base64.b64encode(data).decode('ascii')})
    PAYLOAD.parent.mkdir(exist_ok=True)
    payload=json.dumps({'files':manifest,'uploads':uploads},separators=(',',':'))
    PAYLOAD.write_text(payload,encoding='utf-8')
    print(json.dumps({'characters':len(payload),'chunks':(len(payload)+17999)//18000,'files':len(manifest),'unique_uploads':len(uploads),'bytes':sum(u['size'] for u in uploads.values())}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--chunk',type=int);a=p.parse_args()
    if a.chunk is None:build()
    else:
        text=PAYLOAD.read_text(encoding='utf-8');print(text[a.chunk*18000:(a.chunk+1)*18000],end='')
