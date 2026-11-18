"""Run: python -m backend.analytics.pipeline [--bootstrap 300]."""
from pathlib import Path
import argparse
import json
import time
import numpy as np
import pandas as pd
from .context import ROOT, RAW, load_context, classify, add_baselines
from .scoring import score_players, sensitivity, WEIGHTS, THRESHOLDS

OUT=ROOT/'output'
METHOD = {
    'version':'1.0.0', 'cutoff':'2026-11-11', 'source':'RR supplied data pack',
    'scope':'Descriptive pressure reliability in the supplied 2022-2026 sample; not a forecast or confirmed auction shortlist.',
    'missing':['Primary extras run amounts','Exact running team score and RRR for all chases','Verified 2027 auction availability','Complete injury and domestic form coverage'],
    'pressure_definition': 'Pre-delivery resource stress for batters; established batting resistance for bowlers. Rules are asymmetric because the same wicket can reduce bowling stress while increasing batting stress.',
    'bat_rules': ['Overs 1-6 with at least 2 wickets lost','Overs 7-10 with at least 3 wickets lost and partnership off-bat runs below 30',
                  'Overs 11-15 with at least 5 wickets lost','Second innings, overs 16-20, at least 4 wickets lost',
                  'Knockout, over 11 onward, at least 3 wickets lost'],
    'bowl_rules': ['Overs 16-20 with striker having at least 20 recorded off-bat runs',
                   'Overs 16-20 with at least 35 partnership off-bat runs',
                   'Overs 10-15 with at most 3 wickets lost and striker having at least 30 off-bat runs',
                   'Knockout, over 11 onward, striker at least 15 or partnership at least 25 off-bat runs'],
    'moderate_rules': 'If no high rule: batting is moderate for death phase, 2+ wickets, or knockout; bowling is moderate for death phase, striker 15+, partnership 25+, or knockout. Otherwise normal.',
    'metric_scope': 'Every model run and rate uses legal deliveries in validated, non-revised, completed regular innings only. Legal-ball scoring rate is not official strike rate; off-bat runs per six legal deliveries is not economy. A zero off-bat delivery may still concede extras.',
    'baseline': 'Competition family x match year x phase x innings x batting-position group (bat) or pace/spin (bowl), shrunk with 240 balls toward the matching global phase/innings/role cell.',
    'quality': 'Bat: recorded runs minus expected runs - 12 x (striker-dismissal indicator minus expectation). Bowl: expected runs minus recorded runs + 12 x (credited wicket indicator minus expectation). The 12-run wicket tradeoff is an analyst assumption, not a measured win-probability effect.',
    'normal_comparator': 'All non-high deliveries (normal + moderate); same context adjustment. High and non-high means shrink toward zero with 120 balls.',
    'components': {
        'pressure':'65% percentile of shrunken high-pressure quality + 35% percentile of high-minus-non-high quality.',
        'consistency':'50% percentile of pressure-innings success frequency (quality > 0, minimum 3 high balls, Beta(4,4) smoothing) + 50% inverted percentile of pressure-innings quality variability (8-innings variance prior).',
        'adaptability':'Batter: percentile of mean shrunken quality across observed phases with at least 24 balls. Bowl: this column represents wicket-taking, and is replaced by percentile of context-adjusted credited wicket rate.',
        'efficiency':'Batter: mean of scoring-residual and survival-residual percentiles. Bowl: this column represents run control, and is replaced by percentile of off-bat run suppression.',
        'match_impact':'Unavailable. No calibrated win-probability model or complete score state. Original 10% weight omitted and remaining 90% renormalised.',
        'confidence':'100 x sqrt[high_balls/(high_balls+120) x pressure_innings_with_3plus_balls/(that_count+10)].',
    },
    'weights': WEIGHTS, 'original_weights':{'pressure':.35,'consistency':.20,'adaptability':.15,'efficiency':.15,'match_impact':.10,'confidence':.05},
    'eligibility':THRESHOLDS, 'activity_rule':'At least one eligible appearance in 2025 or 2026. This is a data recency gate, not confirmation of active status.',
    'normalisation':'Midrank empirical percentiles across the eligible category. Ties equal. Component normalization held fixed in bootstrap.',
    'uncertainty':'300 independent within-player innings-cluster bootstrap draws, seed 202711. Resamples all phase and pressure observations of an innings together, recalculates score components, holds eligibility and peer normalization fixed. Conditional 95% intervals do not include classification, cohort or source measurement uncertainty.',
    'validation':'400 Dirichlet weight scenarios (concentration 200), stricter/looser pre-ball rules, wicket-value sensitivity 8/16 runs, opportunity-gate sensitivity, IPL-only comparison, conventional rate comparison and chronological 2022-2024 vs 2025-2026 validation.',
    'limitations':['Extras missing prevents full scoreboard pressure and economy. Source-derived pressure covers resource stress and batting resistance only.',
        'No T20 World Cup, SMAT, VHT or Ranji files supplied. No claim of exhaustive world cricket coverage.',
        'Context cell baselines are in-sample, including each player. Bootstrap holds the baseline fixed.',
        'Adjacent ranks with overlapping intervals are uncertain. Weights and pressure thresholds are analyst choices.',
        'Scoring rate, survival and wickets are related; component weights are a transparent heuristic, not independently estimated effects.',
        'Squad fit is conditional analyst interpretation; no bid prices, purse, nationality or availability inferred.'],
}

def json_clean(x):
    if isinstance(x,dict): return {str(k):json_clean(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)): return [json_clean(v) for v in x]
    if isinstance(x,(np.integer,)): return int(x)
    if isinstance(x,(float,np.floating)): return round(float(x),4) if np.isfinite(x) else None
    if isinstance(x,(np.bool_,)): return bool(x)
    return x

def annotate_bowler(ranked, f, raw):
    # Bowling-specific W and R replace batting A and E at the same weights.
    # score_players accepts a kind and implements these before bootstrap as well.
    return ranked

def pack_player(pid,row,d,kind,weight_test,names):
    col='striker_id' if kind=='bat' else 'bowler_id'
    x=d[d[col].eq(pid)]
    h=x[x[kind+'_pressure'].eq('High')]
    z=x[~x[kind+'_pressure'].eq('High')]
    phases=[]
    for phase,y in x.groupby('phase',observed=True):
        phases.append({'phase':phase,'balls':len(y),'runs':int(y.runs.sum()),'wickets':int(y[kind+'_out'].sum()),
                       'rate':float(y.runs.mean()*(100 if kind=='bat' else 6)), 'impact':float(y[kind+'_quality'].mean())})
    recent=x.sort_values('match_date')
    latest=recent.iloc[-1]
    teams=x.groupby('batting_team_id' if kind=='bat' else 'bowling_team_id').size().sort_values(ascending=False)
    mapping=pd.read_csv(RAW/'teams.csv').drop_duplicates('team_id').set_index('team_id').team_name.to_dict()
    allteams=[mapping.get(int(t),str(t)) for t in teams.index]
    style=x.bowling_type.mode().iloc[0] if kind=='bowl' else x.batting_type.mode().iloc[0]
    position=float(x.batting_order.median()) if kind=='bat' else None
    role=('Top-order batter' if position<=3 else 'Middle-order batter' if position<=5 else 'Lower-order batter') if kind=='bat' else style
    if kind=='bat':
        fit=('Top-order depth and an option to rebuild after early wickets.' if position<=3 else
             'Middle-order continuity when wickets fall and acceleration is needed.' if position<=5 else
             'Lower-order scoring depth after a collapse; assess specialist batting role before bidding.')
        risk='Dataset stress situations may favour rebuilding. Check scoring tempo against the required RR batting role.'
    else:
        peak=max(phases,key=lambda p:p['balls'])['phase']
        fit=f'{peak} bowling depth with a documented test against established batters.'
        risk='Off-bat suppression excludes extras. Validate full economy, fitness and phase fit before any auction decision.'
    pm=[]
    for (mid,inn),g in h.groupby(['match_id','innings']):
        pm.append({'match_id':int(mid),'innings':int(inn),'date':g.match_date.iloc[0],'competition':g.comp_name.iloc[0],
                   'balls':len(g),'runs':int(g.runs.sum()),'wickets':int(g[kind+'_out'].sum()),
                   'impact':float(g[kind+'_quality'].mean()),'source_rows':[int(v) for v in g.source_row]})
    pm=sorted(pm,key=lambda q:q['date'])
    highrate=float(h.runs.mean()*(100 if kind=='bat' else 6))
    normrate=float(z.runs.mean()*(100 if kind=='bat' else 6)) if len(z) else None
    components={k:float(row[k]) for k in WEIGHTS}
    components['match_impact']=None
    return {'id':int(pid),'name':names.get(pid,str(pid)),'category':kind,'rank':int(row['rank']), 'score':float(row.score),
            'score_low':row.score_low,'score_high':row.score_high,'impact_low':row.impact_low,'impact_high':row.impact_high,
            'components':components, 'role':role,'style':style,'teams':allteams,
            'competitions':sorted(x.comp_name.unique().tolist()),'families':sorted(x.family.unique().tolist()),
            'seasons':sorted(x.year.unique().tolist()),'last_seen':latest.match_date,
            'metrics':{'balls':int(row.balls),'runs':int(row.runs),'wickets':int(row.outs),
                       'innings':int(row.innings),'high_balls':int(row.high_balls),'high_innings':int(row.high_innings),
                       'high_runs':int(row.high_runs),'high_wickets':int(row.high_outs),
                       'high_rate':highrate,'normal_rate':normrate,
                       'high_dot_pct':100*float(h.runs.eq(0).mean()),'high_boundary_pct':100*float(h.boundary.mean()),
                       'overall_rate':float(x.runs.mean()*(100 if kind=='bat' else 6)),
                       'pressure_impact':float(row.high_impact),'pressure_lift':float(row.pressure_lift),
                       'high_dismissal_rate':100*float(h[kind+'_out'].mean())},
            'phases':phases,'pressure_matches':pm,'fit':fit,'risk':risk,
            'recommendation':'Priority for further scouting' if row['rank']<=5 else 'Alternative for further scouting',
            'availability':'2027 auction availability unverified','public_research':[],
            'stability':weight_test[str(pid)], 'evidence':'RR proprietary source data; legal-delivery subset',
            'strength':f"High-pressure {'scoring rate' if kind=='bat' else 'off-bat runs / 6'} {highrate:.2f} over {len(h)} legal deliveries; context-adjusted impact {row.high_impact:+.3f} runs per ball.",
            }

def main(bootstrap=300):
    started=time.time()
    OUT.mkdir(exist_ok=True)
    source,audit=load_context()
    data=add_baselines(classify(source))
    roster=pd.read_csv(RAW/'competition_team_player_mapping.csv')
    names=roster.groupby('player_id').player_name.agg(lambda v:v.mode().iloc[0]).to_dict()
    # Source IDs are primary, with only a display-name fallback for unmapped players.
    for idcol,ncol in [('striker_id','striker_name'),('bowler_id','bowler_name')]:
        for pid,name in data.groupby(idcol)[ncol].agg(lambda v:v.mode().iloc[0]).items(): names.setdefault(pid,name)
    rankings={}
    validations={}
    for kind in ['bat','bowl']:
        ranked,f,raw=score_players(data,kind,bootstrap)
        stability=sensitivity(ranked)
        rankings[kind]=[pack_player(pid,row,data,kind,stability,names) for pid,row in ranked.iterrows()]
        ranked.to_csv(OUT/f'{kind}_rankings.csv',index_label='player_id')
        f.to_csv(OUT/f'{kind}_innings_features.csv.gz',index=False,compression='gzip')
        validations[kind]={'eligible_players':len(ranked),'weights':stability,'threshold_tests':[]}
        top=set(ranked.head(10).index)
        for shift,label in [(-1,'Looser pressure rules'),(1,'Stricter pressure rules')]:
            alt=add_baselines(classify(source,shift=shift))
            ar,_,_=score_players(alt,kind)
            atop=set(ar.head(10).index)
            validations[kind]['threshold_tests'].append({'scenario':label,'top10_overlap':len(top&atop),
                 'top10':[names.get(pid,str(pid)) for pid in ar.head(10).index]})
        for value in [8,16]:
            alt=data.copy()
            if kind=='bat': alt['bat_quality']=alt.runs-alt.bat_expected_runs-value*(alt.bat_out-alt.bat_expected_out)
            else: alt['bowl_quality']=alt.bowl_expected_runs-alt.runs+value*(alt.bowl_out-alt.bowl_expected_out)
            ar,_,_=score_players(alt,kind)
            validations[kind]['threshold_tests'].append({'scenario':f'Wicket value {value} runs','top10_overlap':len(top&set(ar.head(10).index)),
                  'top10':[names.get(pid,str(pid)) for pid in ar.head(10).index]})
        # Explicit format separation diagnostic, not an assertion of equivalence.
        ar,_,_=score_players(data[data.family.eq('IPL')],kind)
        validations[kind]['ipl_only']={'eligible_players':len(ar),'top10_overlap':len(top&set(ar.head(10).index)),
                                     'top10':[names.get(pid,str(pid)) for pid in ar.head(10).index]}
        # Chronological holdout uses training-only cells; no future record sets its own expected rate.
        train=add_baselines(classify(source[source.year.le(2024)].copy()))
        test=data[data.year.ge(2025)].copy()
        idcol='striker_id' if kind=='bat' else 'bowler_id'
        # recency gate is removed for training only, keeping the same opportunity thresholds.
        train['year']=2025
        tr,_,_=score_players(train,kind)
        expected_train=source[source.year.le(2024)].copy()
        expected_train=add_baselines(classify(expected_train))
        role='bat_role' if kind=='bat' else 'style'
        keys=['family','phase','innings',role]
        cells=expected_train.groupby(keys).agg(er=('runs','mean'),eo=(kind+'_out','mean'))
        tc=test.join(cells,on=keys)
        globalrun=float(expected_train.runs.mean()); globalout=float(expected_train[kind+'_out'].mean())
        tc['er']=tc.er.fillna(globalrun);tc['eo']=tc.eo.fillna(globalout)
        tc['holdout_quality']=(tc.runs-tc.er-12*(tc[kind+'_out']-tc.eo))*(1 if kind=='bat' else -1)
        hg=tc[tc[kind+'_pressure'].eq('High')].groupby(idcol).agg(n=('runs','size'),mean=('holdout_quality','mean'))
        common=tr.index.intersection(hg[hg.n.ge(50)].index)
        corr=float(tr.loc[common,'score'].corr(hg.loc[common,'mean'],method='spearman')) if len(common)>=5 else None
        validations[kind]['chronological_holdout']={'train':'2022-2024','test':'2025-2026','common_players':len(common),'spearman':corr,
                 'interpretation':'Exploratory association with later pressure impact. Not proof of predictive accuracy. Holdout expectations fitted on training observations only.'}
        # Conventional statistics diagnostic, legal subset, not official career statistics.
        from scipy.stats import spearmanr
        rate=ranked.runs/ranked.balls*(100 if kind=='bat' else 6)
        validations[kind]['conventional_rate_spearman']=float(spearmanr(ranked.score,rate).statistic)
        original=dict(THRESHOLDS[kind])
        try:
            THRESHOLDS[kind].update({k:int(np.ceil(v*1.25)) for k,v in original.items()})
            ar,_,_=score_players(data,kind)
        finally: THRESHOLDS[kind].update(original)
        validations[kind]['higher_opportunity_gate']={'eligible_players':len(ar),'top10_overlap':len(top&set(ar.head(10).index))}
        print(kind, 'eligible',len(ranked),'top10',[(names[pid],round(row.score,2)) for pid,row in ranked.head(10).iterrows()],flush=True)
    distribution=[]
    for kind in ['bat','bowl']:
        for (phase,pressure),g in data.groupby(['phase',kind+'_pressure'],observed=True):
            distribution.append({'category':kind,'phase':phase,'pressure':pressure,'balls':len(g),
                                 'runs':int(g.runs.sum()),'wickets':int(g[kind+'_out'].sum()),
                                 'rate':float(g.runs.mean()*(100 if kind=='bat' else 6))})
    overview={**audit,'players_observed':len(set(data.striker_id)|set(data.bowler_id)),
              'ranked_batters':len(rankings['bat']),'ranked_bowlers':len(rankings['bowl']),
              'competitions':int(data.comp_id.nunique()),'high_batting_balls':int(data.bat_pressure.eq('High').sum()),
              'high_bowling_balls':int(data.bowl_pressure.eq('High').sum()),
              'seasons':sorted(data.year.unique().tolist()),'families':sorted(data.family.unique().tolist()),
              'completed_at':'2026-11-11','model_version':METHOD['version']}
    snapshot={'overview':overview,'methodology':METHOD,'rankings':rankings,'pressure':distribution,'validation':validations,
              'research':[],'dashboard_url':None}
    public=ROOT/'frontend'/'public'
    public.mkdir(parents=True,exist_ok=True)
    cleaned=json_clean(snapshot)
    (OUT/'analysis.json').write_text(json.dumps(cleaned,ensure_ascii=False,indent=2),encoding='utf-8')
    (public/'analysis.json').write_text(json.dumps(cleaned,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    (OUT/'methodology.json').write_text(json.dumps(json_clean(METHOD),indent=2),encoding='utf-8')
    trace=['source_row','match_id','innings','innings_ball_num','overid','striker_id','bowler_id','runs','bat_out','bowl_out',
           'wickets_before','striker_runs_before','partnership_runs_before','bat_pressure','bowl_pressure','bat_reason','bowl_reason',
           'bat_expected_runs','bat_expected_out','bowl_expected_runs','bowl_expected_out','bat_quality','bowl_quality']
    data[trace].to_csv(OUT/'delivery_evidence.csv.gz',index=False,compression='gzip')
    print(json.dumps(json_clean(overview),indent=2))
    print(f'Pipeline completed in {time.time()-started:.1f}s',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--bootstrap',type=int,default=300)
    main(parser.parse_args().bootstrap)
