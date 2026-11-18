"""Rebuild the 20-name shortlist with verified scoreboard context."""
from pathlib import Path
import argparse
import hashlib
import json
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.analytics import shortlist as model
from backend.analytics.scoreboard import recover


def pressure(frame, late_balls=36):
    """Add two pre-ball chase signals. Original pressure triggers still apply."""
    result = model.classify(frame)
    runs_needed = result.target - result.score_before
    balls = result.balls_left
    wickets_in_hand = 10 - result.verified_wickets_before
    rate = 6 * runs_needed / balls.where(balls.gt(0))
    opening_rate = result.target / 20
    # Feasibility bounds are explicit heuristics. Less batting depth lowers the upper bound.
    upper = (opening_rate + 4 - 1.5 * (3 - wickets_in_hand).clip(lower=0)).clip(upper=18)
    live = result.target.notna() & runs_needed.gt(0) & balls.gt(0) & wickets_in_hand.gt(0)
    contested = live & balls.le(late_balls) & rate.ge((opening_rate - 2.5).clip(lower=5)) & rate.le(upper)
    steep = live & balls.le(60) & rate.ge((opening_rate + 1.5).clip(lower=9)) & rate.le(upper)
    result['required_run_rate'] = rate.where(live)
    for kind, add in [('bat', contested | steep), ('bowl', contested)]:
        result[kind + '_scoreboard_high'] = add
        new = result[kind + '_pressure'].ne('High') & add
        result.loc[new, kind + '_pressure'] = 'High'
        result.loc[new, kind + '_reason'] = np.where(contested[new], 'Contested chase finish', 'Steep but feasible chase')
        result[kind + '_high_added'] = new
    return result


def standardize(base, state, legacy):
    merged = base.merge(state, on='source_row', how='left', validate='one_to_one')
    matched = merged.verified_legal.notna()
    merged['verified'] = matched
    # The public match has passed full-innings identity, allocation and scoreboard checks.
    # For unmatched records use exactly the earlier eligibility policy.
    keep = merged.source_row.isin(legacy.source_row) & ~matched
    keep |= merged.verified_legal.eq(True)
    legal = merged[keep].copy()
    legal.loc[legal.verified, 'wickets_before'] = legal.loc[legal.verified, 'verified_wickets_before']
    return legal, merged[matched].copy()


def common_holdout(frame, enhanced):
    """Train on earlier matches, compare against the same later verified chase target."""
    legacy_labels = model.classify(frame)
    results = {kind: [] for kind in model.KINDS}
    for year in (2024, 2025, 2026):
        train = enhanced[enhanced.year.lt(year)].copy()
        test = enhanced[enhanced.year.eq(year) & enhanced.target.notna()].copy()
        original = legacy_labels.loc[train.index]
        assert not set(train.match_id) & set(test.match_id)
        for kind in model.KINDS:
            peer = model.PeerExpectations(train, kind)
            cols = [kind + '_run_value', kind + '_wicket_value']
            for data in (train, test):
                data[cols[0]], data[cols[1]] = peer.residuals(data, kind)
            test_pressure = test[test[kind + '_pressure'].eq('High')]
            observations = model.innings_stats(test_pressure, kind).groupby('player_id').agg(
                balls=('balls','sum'), matches=('match_id','nunique'), quality=('quality','sum'))
            observations = observations[observations.balls.ge(24) & observations.matches.ge(3)]
            old = train.assign(**{kind + '_pressure': original[kind + '_pressure']})
            scores = []
            for data in (train, old):
                means = {}
                per_innings = model.innings_stats(data[data[model.PID[kind]].isin(observations.index)], kind)
                for pid, row in per_innings.groupby('player_id'):
                    sample = row.groupby('match_id')[model.STATS].sum()
                    high_matches = sample.high_balls.gt(0).sum()
                    if high_matches < 4:
                        continue
                    estimate = model.estimates(sample, kind, pid)
                    if estimate is not None and estimate['score'] is not None:
                        means[int(pid)] = estimate['score']
                scores.append(means)
            for scope, allowed in [('all', set(observations.index)), ('screenshot', {p.player_id(kind) for p in model.POOL})]:
                ids = sorted(allowed & set(scores[0]) & set(scores[1]))
                target = (6 * observations.quality / observations.balls).loc[ids].tolist()
                results[kind].append({'year': year, 'scope': scope, 'players': len(ids),
                    'scoreboard_rho': model.rho([scores[0][pid] for pid in ids], target),
                    'legacy_rho': model.rho([scores[1][pid] for pid in ids], target)})
    return results


def extras_audit(events, pid):
    # All ball events contribute actual charged runs. Byes, leg-byes and general penalties do not.
    cost = events[events.bowler_id.eq(pid)]
    balls = int(cost.verified_legal.sum())
    runs = int(cost.runs.sum() + cost.charged_extras.sum())
    return {'legal_balls': balls, 'runs_charged': runs, 'wide_noball_extras': int(cost.charged_extras.sum()),
            'charged_runs_per_over': None if not balls else round(6 * runs / balls, 2)}


def build(archive_dir):
    paths = [archive_dir / name for name in ('ipl_json.zip', 't20s_male_json.zip')]
    base, _ = model.load_context(cutoff=model.CUTOFF)
    base = base[base.match_date.le(model.CUTOFF)].copy()
    legacy, _, _ = model.audited_deliveries(base)
    state, links = recover(base, paths)
    if state.empty:
        raise ValueError('Public archives contain no verified match overlap')
    frame, public_events = standardize(base, state, legacy)
    classified = pressure(frame)
    enhanced = model.with_context(classified)
    roster = pd.read_csv(model.RAW / 'competition_team_player_mapping.csv')
    identities = model.identity_audit(roster, base)
    rankings = {kind: model.candidate_results(enhanced, kind, identities, details=True) for kind in model.KINDS}
    model.bounded_rank_check(rankings)
    earlier = json.loads((ROOT / 'output/shortlist/shortlist.json').read_text(encoding='utf-8'))
    flat = []
    sensitivity = {}
    for kind in model.KINDS:
        side = rankings[kind]
        old_rank = {p['id']: p['rank'] for p in earlier['categories'][kind]['ranking']}
        main_ids = {p['id'] for p in side['ranking']}
        sensitivity[kind] = []
        for label, subset in [('24-ball finish', pressure(enhanced, 24)), ('42-ball finish', pressure(enhanced, 42)),
                               ('Verified matches only', model.with_context(enhanced[enhanced.verified])),
                               ('Restored deliveries with original pressure rules', model.classify(enhanced))]:
            alternative = model.candidate_results(subset, kind, identities)['ranking']
            sensitivity[kind].append({'scenario': label, 'ranked': len(alternative),
                 'top_ten_overlap': len(main_ids & {p['id'] for p in alternative}), 'order': [p['name'] for p in alternative]})
        for p in side['candidates']:
            player = enhanced[enhanced[model.PID[kind]].eq(p['id'])]
            p['scoreboard'] = {'previous_rank': old_rank.get(p['id']), 'verified_balls': int(player.verified.sum()),
                'verified_chase_balls': int(player.target.notna().sum()),
                'added_high_balls': int(player[kind + '_high_added'].sum())}
            if kind == 'bowl':
                p['scoreboard']['verified_charges'] = extras_audit(public_events, p['id'])
            if p['rank']:
                flat.append({'category': kind, 'rank': p['rank'], 'name': p['name'], 'identity': p['affiliation'], 'id': p['id'],
                    'tier': p['tier'], 'high_balls': p['sample']['high_balls'], 'high_matches': p['sample']['high_matches'],
                    'verified_chase_balls': p['scoreboard']['verified_chase_balls'],
                    'added_high_balls': p['scoreboard']['added_high_balls'], 'score': p['estimates']['score'],
                    'previous_rank': p['scoreboard']['previous_rank']})
    # Quantify the effect of extras on the new triggers. Keep the verified target fixed and omit chase extras only.
    off_bat = public_events.groupby(['match_id', 'innings']).runs.cumsum() - public_events.runs
    no_extras_scores = pd.Series(off_bat.to_numpy(), index=public_events.source_row)
    counterfactual = enhanced.assign(score_before=enhanced.source_row.map(no_extras_scores))
    without = pressure(counterfactual)
    metadata = {
        'public_sources': [{'url': 'https://cricsheet.org/downloads/' + p.name,
                            'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths],
        'local_match_count': int(base.match_id.nunique()), 'verified_matches': int(links.cricsheet_id.notna().sum()),
        'verified_by_family': links[links.cricsheet_id.notna()].groupby('family').size().to_dict(),
        'verified_events': len(state), 'verified_extras_runs': int(state.verified_extras.sum()),
        'verified_chase_legal_balls': int(enhanced.target.notna().sum()), 'scored_legal_balls': len(enhanced),
        'restored_legal_balls': int((~enhanced.source_row.isin(legacy.source_row)).sum()),
        'added_high_pressure_balls': {k: int(enhanced[k + '_high_added'].sum()) for k in model.KINDS},
        'extras_changed_high_labels': {k: int(enhanced[k + '_pressure'].ne(without[k + '_pressure']).sum()) for k in model.KINDS},
        'cutoff': model.CUTOFF, 'previous_snapshot': earlier['build_id'],
    }
    output = ROOT / 'output/shortlist'
    result = {'audit': metadata, 'rankings': rankings, 'sensitivity': sensitivity, 'holdout': common_holdout(frame, classified)}
    state = state.merge(base[['source_row', 'match_id', 'innings', 'innings_ball_num']], on='source_row', validate='one_to_one')
    state['runs_needed'] = state.target - state.score_before
    state['required_run_rate'] = 6 * state.runs_needed / state.balls_left.where(state.balls_left.gt(0))
    links.to_csv(output / 'Cricsheet_Match_Crosswalk.csv', index=False)
    state.to_csv(output / 'Verified_Scoreboard.csv.gz', index=False)
    pd.DataFrame(flat).to_csv(output / 'Scoreboard_Form_Selections.csv', index=False, encoding='utf-8-sig')
    (output / 'scoreboard_results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    return metadata, flat, result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archives', type=Path, default=ROOT/'tmp/cricsheet')
    audit, rows, results = build(parser.parse_args().archives)
    print(json.dumps(audit, indent=2))
    print(pd.DataFrame(rows)[['category','rank','name','tier','high_balls','high_matches','added_high_balls','score','previous_rank']].to_string(index=False))
    print(json.dumps({key: results[key] for key in ['sensitivity', 'holdout']}, indent=2))
