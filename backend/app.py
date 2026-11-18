"""Read-only hosted API, with explicit local-only administrative operations."""
from pathlib import Path
from functools import lru_cache
from typing import Literal
import csv
import io
import json
import os
import secrets
import subprocess
import sys
import threading
import html

from fastapi import FastAPI, HTTPException, Query, Header, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse, Response
from pydantic import BaseModel, Field

ROOT=Path(__file__).resolve().parents[1]
MODULE=Path(__file__).resolve().parent
DEFAULT_SNAPSHOT=ROOT/'output'/'analysis.json' if (ROOT/'output'/'analysis.json').exists() else MODULE/'data'/'analysis.json'
SNAPSHOT=Path(os.getenv('SUPERR_ANALYSIS_PATH',str(DEFAULT_SNAPSHOT)))
app=FastAPI(title='SupeRR Auction Intelligence',version='1.0.0',description='Explainable legal-ball pressure reliability. Rankings are descriptive, not auction availability or future predictions.')
origins=[s.strip() for s in os.getenv('CORS_ORIGINS','http://127.0.0.1:5173,http://localhost:5173').split(',') if s.strip()]
app.add_middleware(CORSMiddleware,allow_origins=origins,allow_methods=['GET','POST'],allow_headers=['Content-Type','X-Admin-Token'])
lock=threading.Lock()

@lru_cache(maxsize=4)
def read_version(path:str,mtime:int):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def snapshot():
    if not SNAPSHOT.exists(): raise HTTPException(503,'Analysis missing. Run python -m backend.analytics.pipeline first.')
    return read_version(str(SNAPSHOT),SNAPSHOT.stat().st_mtime_ns)

def pool(kind:str): return snapshot()['rankings'][kind]
def player(pid:int,kind:str|None=None):
    result=[p for k in ([kind] if kind else ['bat','bowl']) for p in pool(k) if p['id']==pid]
    if not result: raise HTTPException(404,'Player not in the eligible ranked cohort.')
    return result[0] if kind else result

def filtered(kind,q='',family=None,season=None,role=None):
    return [p for p in pool(kind) if q.casefold() in p['name'].casefold() and (not family or family in p['families'])
            and (not season or season in p['seasons']) and (not role or role==p['role'])]

@app.get('/api/health')
def health(): return {'status':'ok','model_version':snapshot()['overview']['model_version'],'raw_data_available':(ROOT/'6af3166e7b922_data_pack').exists()}

@app.get('/api/snapshot')
def get_snapshot(): return snapshot()

@app.get('/api/overview')
def overview(): return snapshot()['overview']

@app.get('/api/players/compare')
def compare(ids:str=Query(pattern=r'^\d+(,\d+){0,3}$'),category:Literal['bat','bowl']='bat'):
    selected=list(dict.fromkeys(int(v) for v in ids.split(',')))
    return {'category':category,'players':[player(pid,category) for pid in selected]}

@app.get('/api/players')
def players(q:str=Query('',max_length=100),category:Literal['bat','bowl']='bat',family:str|None=None,
            season:int|None=Query(None,ge=2022,le=2026),role:str|None=None,
            page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=100)):
    rows=filtered(category,q,family,season,role)
    return {'items':rows[(page-1)*page_size:page*page_size],'total':len(rows),'page':page,'page_size':page_size,
            'filter_scope':'Player coverage only. Published full-window score and rank retained.'}

@app.get('/api/players/{player_id}')
def profile(player_id:int): return {'profiles':player(player_id)}

def rankings(kind,q,family,season,role,sort,descending,page,page_size):
    rows=filtered(kind,q,family,season,role)
    key=(lambda p:p['score']) if sort=='score' else (lambda p:p['metrics'][sort])
    rows=sorted(rows,key=key,reverse=descending)
    return {'items':rows[(page-1)*page_size:page*page_size],'total':len(rows),'page':page,'page_size':page_size,
            'filter_scope':'Coverage filters retain published full-window rank; not recalculated subset ranks.'}

@app.get('/api/{discipline}/rankings')
def ranked(discipline:Literal['batters','bowlers'],q:str=Query('',max_length=100),family:str|None=None,
           season:int|None=Query(None,ge=2022,le=2026),role:str|None=None,
           sort:Literal['score','high_balls','high_rate','pressure_impact']='score',descending:bool=True,
           page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=100)):
    return rankings('bat' if discipline=='batters' else 'bowl',q,family,season,role,sort,descending,page,page_size)

@app.get('/api/{discipline}/{player_id}/reliability')
def reliability(discipline:Literal['batters','bowlers'],player_id:int):
    p=player(player_id,'bat' if discipline=='batters' else 'bowl')
    return {k:p[k] for k in ['id','name','score','score_low','score_high','components','stability']}

@app.get('/api/analytics/pressure')
def pressure(category:Literal['bat','bowl']='bat',level:Literal['High','Moderate','Normal']|None=None):
    return [r for r in snapshot()['pressure'] if r['category']==category and (not level or r['pressure']==level)]

@app.get('/api/analytics/phase-wise')
def phase_wise(player_id:int,category:Literal['bat','bowl']='bat'): return player(player_id,category)['phases']

@app.get('/api/analytics/consistency')
def consistency(player_id:int,category:Literal['bat','bowl']='bat'): return player(player_id,category)['pressure_matches']

@app.get('/api/auction/recommendations')
def auction(category:Literal['bat','bowl']='bat'):
    return {'availability':'Unverified for every player. Statistical ranking is not an available-to-buy list.',
            'items':pool(category)[:10]}

@app.get('/api/methodology')
def methodology(): return snapshot()['methodology']

@app.get('/api/data-quality')
def data_quality():
    d=snapshot()
    return {'overview':d['overview'],'missing':d['methodology']['missing'],'limitations':d['methodology']['limitations'],
            'validation':d['validation']}

@app.get('/api/export/rankings.csv')
def export(category:Literal['bat','bowl']='bat'):
    out=io.StringIO();writer=csv.writer(out)
    writer.writerow(['rank','player_id','name','score','95_low','95_high','high_legal_balls','high_rate','availability'])
    for p in pool(category):
        writer.writerow([p['rank'],p['id'],p['name'],p['score'],p['score_low'],p['score_high'],p['metrics']['high_balls'],p['metrics']['high_rate'],p['availability']])
    return StreamingResponse(iter([out.getvalue()]),media_type='text/csv',headers={'Content-Disposition':f'attachment; filename="superr-{category}-rankings.csv"'})

@app.get('/api/players/{player_id}/report')
def player_report(player_id:int,category:Literal['bat','bowl']='bat'):
    p=player(player_id,category)
    report=ROOT/'output'/'pdf'/'players'/f'{category}-{player_id}.pdf'
    if report.exists():return FileResponse(report,filename=f"{p['name']}-scouting.pdf",media_type='application/pdf')
    try:
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
    except ImportError: raise HTTPException(503,'PDF runtime unavailable. Download the complete report from the dashboard.')
    out=io.BytesIO();styles=getSampleStyleSheet();doc=SimpleDocTemplate(out,title=p['name']+' - SupeRR Scouting')
    metrics=p['metrics']
    story=[Paragraph(html.escape(p['name']),styles['Title']),Spacer(1,12)]
    texts=[f"SupeRR Selector | {'Batting' if category=='bat' else 'Bowling'} rank {p['rank']} | Score {p['score']:.2f}/100",
           f"Role: {p['role']}. Source teams: {', '.join(p['teams'])}.",
           f"Conditional 95% score interval: {p['score_low']:.1f}-{p['score_high']:.1f}. High-pressure sample: {metrics['high_balls']} legal balls in {metrics['high_innings']} innings.",
           p['strength'],'Potential RR role: '+p['fit'],'Risk: '+p['risk'],'Availability: '+p['availability'],
           'Source: RR supplied data pack, validated legal-delivery subset. Bowling rate excludes extras. Scores describe the supplied sample, not future performance.']
    texts += [s['title']+': '+s['url'] for s in p['public_research']]
    for text in texts:story += [Paragraph(html.escape(text),styles['BodyText']),Spacer(1,12)]
    doc.build(story)
    return Response(out.getvalue(),media_type='application/pdf',headers={'Content-Disposition':f'attachment; filename="superr-{category}-{player_id}.pdf"'})

def require_admin(token):
    configured=os.getenv('SUPERR_ADMIN_TOKEN')
    if not configured or not token or not secrets.compare_digest(configured,token):
        raise HTTPException(403,'Administrative operations require SUPERR_ADMIN_TOKEN and X-Admin-Token.')
    if os.getenv('VERCEL') or not (ROOT/'6af3166e7b922_data_pack').exists():
        raise HTTPException(503,'Data ingestion and recalculation run in the local research workspace, not the read-only hosted API.')

@app.post('/api/data/upload')
async def upload(request:Request,filename:str=Query(pattern=r'^[a-z][a-z0-9_]{0,60}\.csv$'),x_admin_token:str|None=Header(None)):
    require_admin(x_admin_token)
    # Uploads are staged; never overwrite proprietary originals or execute supplied text.
    content=await request.body()
    if len(content)>50*1024*1024: raise HTTPException(413,'Maximum staged CSV size is 50 MB.')
    try:
        text=content.decode('utf-8-sig'); header=next(csv.reader(io.StringIO(text)))
        if len(header)<2 or len(set(header))!=len(header): raise ValueError('Invalid column header')
    except (UnicodeError,ValueError,StopIteration): raise HTTPException(422,'Expected a UTF-8 CSV with unique column headers.')
    staging=ROOT/'data'/'staged';staging.mkdir(parents=True,exist_ok=True)
    dest=staging/filename
    if dest.exists(): raise HTTPException(409,'A staged file already uses this name. Originals are never overwritten.')
    dest.write_bytes(content)
    return {'status':'staged','filename':filename,'columns':header,'next':'Review the staging schema and explicitly integrate it into a new version of the raw pack. It is not yet used in rankings.'}

class Recalculate(BaseModel):
    bootstrap:int=Field(300,ge=50,le=1000)

@app.post('/api/analytics/recalculate',status_code=202)
def recalculate(body:Recalculate,tasks:BackgroundTasks,x_admin_token:str|None=Header(None)):
    require_admin(x_admin_token)
    if not lock.acquire(blocking=False):raise HTTPException(409,'An analysis is already running.')
    def run():
        try: subprocess.run([sys.executable,'-m','backend.analytics.pipeline','--bootstrap',str(body.bootstrap)],cwd=ROOT,check=True)
        finally: lock.release();read_version.cache_clear()
    tasks.add_task(run)
    return {'status':'accepted','message':'Local analysis will recompute from the original data pack.'}
