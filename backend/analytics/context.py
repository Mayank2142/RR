from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / '6af3166e7b922_data_pack'
CREDITED = {'Caught', 'Bowled', 'LBW', 'Stump', 'Hit Wicket'}

def load_context(raw=RAW, cutoff='2026-11-11'):
    """Build only observable pre-delivery context. Never impute missing extras."""
    b = pd.read_csv(raw/'ball_by_ball.csv', low_memory=False)
    m = pd.read_csv(raw/'matches.csv')
    c = pd.read_csv(raw/'competitions.csv')
    b['source_row'] = np.arange(len(b)) + 2
    if b.duplicated(['match_id','innings','innings_ball_num']).any():
        raise ValueError('Duplicate delivery keys. Resolve the source rather than silently dropping records.')
    b = b.merge(m, on='match_id', how='left', validate='many_to_one').merge(c, on='comp_id', how='left', validate='many_to_one')
    b = b.sort_values(['match_id','innings','innings_ball_num'], kind='stable').reset_index(drop=True)
    b['legal'] = ~b.extras_type.isin(['wide','Overstep'])
    b['phase'] = pd.cut(b.overid, [0,6,15,20], labels=['Powerplay','Middle','Death']).astype(str)
    b['family'] = np.where(b.comp_name.str.startswith('IPL '), 'IPL', np.where(b.match_format.eq('T20I'),'T20I','Emerging T20'))
    b['year'] = pd.to_datetime(b.match_date).dt.year
    innings_keys = ['match_id','innings']
    # An ambiguous event can change the legal-ball denominator. Quarantine its whole innings.
    b['ambiguous'] = b.extras_type.isin(['other','Penalty']) | (b.extras_type.isin(['byes','legbyes']) & b.runs.ne(0))
    og = b.groupby(innings_keys+['overid']).legal.sum().rename('legal_count').reset_index()
    og['last_over'] = og.groupby(innings_keys).overid.transform('max')
    og['bad'] = ((og.overid.lt(og.last_over)) & og.legal_count.ne(6)) | og.legal_count.gt(6)
    bad_overs = og.groupby(innings_keys).bad.any()
    gaps = b.groupby(innings_keys).innings_ball_num.agg(['min','max','count'])
    gaps['gap'] = gaps['min'].ne(1) | gaps['max'].ne(gaps['count'])
    bad_innings = set(bad_overs[bad_overs].index) | set(gaps[gaps.gap].index)
    b['sequence_bad'] = pd.MultiIndex.from_frame(b[innings_keys]).isin(bad_innings)
    b['ambiguous_innings'] = b.groupby(innings_keys).ambiguous.transform('any')
    b['revised'] = b[['first_inn_revised_overs','second_inn_revised_overs','revised_target']].notna().any(axis=1)
    b['unfinished'] = b.result.fillna('').str.contains('no result|abandon|cancel', case=False, regex=True)
    b['eligible_context'] = (b.innings.isin([1,2]) & ~b.revised & ~b.unfinished & ~b.ambiguous_innings
                             & ~b.sequence_bad & b.match_date.le(cutoff))
    # Score and wickets always exclude the current delivery.
    b['wickets_before'] = b.groupby(innings_keys).is_wicket.cumsum() - b.is_wicket.astype(int)
    b['striker_runs_before'] = b.groupby(innings_keys+['striker_id']).runs.cumsum() - b.runs
    # Partnership includes off-bat runs only, and resets AFTER a wicket.
    b['partnership_id'] = b['wickets_before']
    b['partnership_runs_before'] = b.groupby(innings_keys+['partnership_id']).runs.cumsum() - b.runs
    b['bat_out'] = (b.is_wicket & b.dismissed_player_id.eq(b.striker_id)).astype(int)
    b['bowl_out'] = (b.is_wicket & b.dismissal_type.isin(CREDITED)).astype(int)
    b['boundary'] = (b.is_four | b.is_six).astype(int)
    b['bat_role'] = np.select([b.batting_order.le(3), b.batting_order.le(5)], ['Top order','Middle order'], default='Lower order')
    b['style'] = b.pace_or_spin.fillna('Unknown')
    audit = {
        'source_deliveries': len(b), 'source_matches': int(b.match_id.nunique()), 'metadata_matches': len(m),
        'valid_innings': int(b[b.eligible_context].groupby(innings_keys).ngroups),
        'valid_matches': int(b[b.eligible_context].match_id.nunique()),
        'valid_delivery_events': int(b.eligible_context.sum()),
        'legal_model_deliveries': int((b.eligible_context & b.legal).sum()),
        'exclusions_overlapping': {name: int(b[mask].groupby(innings_keys).ngroups) for name,mask in {
            'ambiguous_extra_innings': b.ambiguous_innings, 'sequence_inconsistent_innings': b.sequence_bad,
            'revised_match_innings': b.revised, 'unfinished_match_innings': b.unfinished, 'super_over_innings': b.innings.gt(2)}.items()},
        'source_date_min': m.match_date.min(), 'source_date_max': m.match_date.max(),
        'missing_match_deliveries': int(len(set(m.match_id)-set(b.match_id))),
    }
    return b, audit

def classify(b, shift=0):
    """Separate batting resource stress and bowling resistance; no outcome/target inputs."""
    b = b.copy()
    w, o, r, p = b.wickets_before, b.overid, b.striker_runs_before, b.partnership_runs_before
    bat_rules = {
        'Early collapse': (o.le(6) & w.ge(2+shift)),
        'Rebuild after collapse': (o.between(7,10) & w.ge(3+shift) & p.lt(30)),
        'Limited batting resources': (o.between(11,15) & w.ge(5+shift)),
        'Late chase with depleted wickets': (b.innings.eq(2) & o.ge(16) & w.ge(4+shift)),
        'Knockout with resource stress': (b.knock_out.eq(1) & o.ge(11) & w.ge(3+shift)),
    }
    bowl_rules = {
        'Established batter in death overs': (o.ge(16) & r.ge(20+shift*5)),
        'Set partnership in death overs': (o.ge(16) & p.ge(35+shift*5)),
        'Middle overs against set batter': (o.between(10,15) & w.le(3) & r.ge(30+shift*5)),
        'Knockout against established batting': (b.knock_out.eq(1) & o.ge(11) & (r.ge(15+shift*5) | p.ge(25+shift*5))),
    }
    for kind, rules in [('bat',bat_rules),('bowl',bowl_rules)]:
        high = np.logical_or.reduce(list(rules.values()))
        moderate = ((o.ge(16) | w.ge(2) | b.knock_out.eq(1)) if kind=='bat' else
                    (o.ge(16) | r.ge(15) | p.ge(25) | b.knock_out.eq(1)))
        b[kind+'_pressure'] = np.select([high,moderate], ['High','Moderate'], default='Normal')
        b[kind+'_reason'] = np.select(list(rules.values()), list(rules), default='No high-pressure trigger')
    return b

def add_baselines(b):
    """Shrink context cells toward phase means. All estimates are descriptive in-sample."""
    d = b[b.eligible_context & b.legal].copy()
    for kind, role, out in [('bat','bat_role','bat_out'),('bowl','style','bowl_out')]:
        keys = ['family','year','phase','innings',role]
        # Global fallback is phase + innings + relevant role (not competition reputation).
        fallback = d.groupby(['phase','innings',role]).agg(pruns=('runs','mean'),pout=(out,'mean'))
        cell = d.groupby(keys).agg(n=('runs','size'),sruns=('runs','sum'),sout=(out,'sum'))
        cell = cell.join(fallback, on=['phase','innings',role])
        cell['expected_runs'] = (cell.sruns + 240*cell.pruns)/(cell.n+240)
        cell['expected_out'] = (cell.sout + 240*cell.pout)/(cell.n+240)
        d = d.join(cell[['expected_runs','expected_out']].rename(columns=lambda x: kind+'_'+x), on=keys)
        if kind=='bat':
            d['bat_quality'] = d.runs-d.bat_expected_runs - 12*(d.bat_out-d.bat_expected_out)
            d['bat_rate_residual'] = d.runs-d.bat_expected_runs
            d['bat_out_residual'] = d.bat_expected_out-d.bat_out
        else:
            d['bowl_quality'] = d.bowl_expected_runs-d.runs + 12*(d.bowl_out-d.bowl_expected_out)
            d['bowl_rate_residual'] = d.bowl_expected_runs-d.runs
            d['bowl_out_residual'] = d.bowl_out-d.bowl_expected_out
    return d
