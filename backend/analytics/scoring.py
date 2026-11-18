import numpy as np
import pandas as pd

SEED = 202711
WEIGHTS = {'pressure':35/90, 'consistency':20/90, 'adaptability':15/90, 'efficiency':15/90, 'confidence':5/90}
THRESHOLDS = {'bat': {'balls':300,'high_balls':80,'innings':15,'high_innings':8},
              'bowl': {'balls':360,'high_balls':100,'innings':15,'high_innings':10}}

def ecdf(values, reference):
    """Midrank empirical percentile, ties remain equal, on a fixed eligible peer pool."""
    x = np.sort(np.asarray(reference, dtype=float))
    v = np.asarray(values, dtype=float)
    return 100*(np.searchsorted(x,v,'left')+np.searchsorted(x,v,'right'))/(2*len(x))

def match_features(d, kind):
    pid = 'striker_id' if kind=='bat' else 'bowler_id'
    q = kind+'_quality'
    x=d.copy()
    x['high'] = x[kind+'_pressure'].eq('High').astype(int)
    x['hq'] = x[q]*x.high
    x['normal'] = 1-x.high
    x['nq'] = x[q]*x.normal
    x['ho'] = x[kind+'_out_residual']*x.high
    x['hr'] = x[kind+'_rate_residual']*x.high
    x['high_runs'] = x.runs*x.high
    x['high_outs'] = x[kind+'_out']*x.high
    x['high_boundary'] = x.boundary*x.high
    x['high_dot'] = x.runs.eq(0)*x.high
    x['dot'] = x.runs.eq(0).astype(int)
    cols={'balls':('runs','size'),'runs':('runs','sum'),'outs':(kind+'_out','sum'),
          'quality':(q,'sum'),'rate':(kind+'_rate_residual','sum'),'outres':(kind+'_out_residual','sum'),
          'high_balls':('high','sum'),'high_quality':('hq','sum'),'normal_balls':('normal','sum'),'normal_quality':('nq','sum'),
          'high_runs':('high_runs','sum'),'high_outs':('high_outs','sum'),
          'boundaries':('boundary','sum'),'high_boundaries':('high_boundary','sum'),
          'dots':('dot','sum'),'high_dots':('high_dot','sum')}
    g=x.groupby([pid,'match_id','innings']).agg(**cols).reset_index().rename(columns={pid:'player_id'})
    phase=x.groupby([pid,'match_id','innings','phase']).agg(n=('runs','size'),q=(q,'sum')).unstack('phase',fill_value=0)
    phase.columns=[a+'_'+b for a,b in phase.columns]
    g=g.merge(phase, left_on=['player_id','match_id','innings'],right_index=True)
    g['high_effective'] = (g.high_balls>=3).astype(int)
    g['high_mean'] = g.high_quality/g.high_balls.clip(lower=1)
    g['high_success'] = (g.high_mean.gt(0)&g.high_effective.eq(1)).astype(int)
    g['high_moment1'] = g.high_mean*g.high_effective
    g['high_moment2'] = g.high_mean**2*g.high_effective
    return g

def raw_features(s):
    """Arrays with last axis as features; supports point estimates and bootstrap draws."""
    n, hn = np.maximum(s['balls'],1), s['high_balls']
    nh = np.maximum(s['normal_balls'],1)
    hp = s['high_quality']/(hn+120)  # zero-centered context prior of 120 legal balls
    normal = s['normal_quality']/(nh+120)
    lift = hp-normal
    k=s['high_effective']
    success=(s['high_success']+4)/(k+8)
    mean=s['high_moment1']/np.maximum(k,1)
    variance=np.maximum(s['high_moment2']/np.maximum(k,1)-mean**2,0)
    # Variability shrunk to a fixed 1 run/ball variance, before percentile inversion.
    stability= -np.sqrt((variance*k+8)/(k+8))
    phase_values=[]
    for p in ['Powerplay','Middle','Death']:
        phase_values.append(np.where(s['n_'+p]>=24, s['q_'+p]/(s['n_'+p]+120), np.nan))
    pv=np.stack(phase_values,axis=-1)
    # Only observed phases with >=24 balls. Missing phases contribute no score.
    adaptation=np.nanmean(pv,axis=-1)
    adaptation=np.where(np.isfinite(adaptation),adaptation,0)
    conf=100*np.sqrt((hn/(hn+120))*(k/(k+10)))
    return {'hp':hp,'lift':lift,'success':success,'stability':stability,'adaptability':adaptation,
            'rate':s['rate']/(n+240),'outres':s['outres']/(n+240),'confidence':conf}

def components(raw, ref, kind='bat'):
    pct=lambda k:ecdf(raw[k],ref[k])
    return {'pressure':.65*pct('hp')+.35*pct('lift'),
            'consistency':.5*pct('success')+.5*pct('stability'),
            'adaptability':pct('adaptability') if kind=='bat' else pct('outres'),
            'efficiency':.5*pct('rate')+.5*pct('outres') if kind=='bat' else pct('rate'),
            'confidence':raw['confidence']}

def score_players(d,kind,bootstrap=0):
    f=match_features(d,kind)
    sums=f.groupby('player_id').sum(numeric_only=True).drop(columns=['match_id','innings'])
    sums['innings']=f.groupby('player_id').size()
    sums['high_innings']=f[f.high_balls>0].groupby('player_id').size().reindex(sums.index,fill_value=0)
    latest=d.groupby('striker_id' if kind=='bat' else 'bowler_id').year.max()
    t=THRESHOLDS[kind]
    mask=np.logical_and.reduce([sums[c].ge(v) for c,v in t.items()]) & latest.reindex(sums.index).ge(2025)
    eligible=sums[mask].copy()
    raw=raw_features({c:eligible[c].to_numpy() for c in eligible.columns})
    comp=components(raw,raw,kind)
    for k,v in comp.items(): eligible[k]=v
    eligible['score']=sum(eligible[k]*v for k,v in WEIGHTS.items())
    eligible['high_impact']=raw['hp']
    eligible['pressure_lift']=raw['lift']
    eligible['score_low']=np.nan
    eligible['score_high']=np.nan
    eligible['impact_low']=np.nan
    eligible['impact_high']=np.nan
    if bootstrap:
        rng=np.random.default_rng(SEED+(kind=='bowl'))
        for pid,g in f[f.player_id.isin(eligible.index)].groupby('player_id'):
            n=len(g)
            weights=rng.multinomial(n,np.full(n,1/n),size=bootstrap)
            draws={c:weights@g[c].to_numpy(dtype=float) for c in sums.columns if c not in ['innings','high_innings']}
            br=raw_features(draws)
            bc=components(br,raw,kind)
            scores=sum(bc[k]*v for k,v in WEIGHTS.items())
            eligible.loc[pid,['score_low','score_high']]=np.quantile(scores,[.025,.975])
            eligible.loc[pid,['impact_low','impact_high']]=np.quantile(br['hp'],[.025,.975])
    eligible=eligible.sort_values(['score','high_balls'],ascending=False)
    eligible['rank']=np.arange(1,len(eligible)+1)
    return eligible,f,raw

def sensitivity(ranked, scenarios=400):
    rng=np.random.default_rng(SEED)
    keys=list(WEIGHTS)
    weights=rng.dirichlet(np.array(list(WEIGHTS.values()))*200,size=scenarios)
    scores=ranked[keys].to_numpy()@weights.T
    ranks=np.argsort(np.argsort(-scores,axis=0),axis=0)+1
    return {str(pid):{'top10_weight_frequency':round(float(np.mean(ranks[i]<=10))*100,1),
                     'weight_rank_min':int(ranks[i].min()),'weight_rank_max':int(ranks[i].max())}
            for i,pid in enumerate(ranked.index)}
