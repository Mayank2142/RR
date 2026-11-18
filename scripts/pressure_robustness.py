"""Audit the shortlist for dependence on one match and changes of cricket context."""
from pathlib import Path
import sys
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.analytics.shortlist import (
    CUTOFF, PID, STATS, POOL, load_context, audited_deliveries, classify,
    with_context, innings_stats, measures, estimates,
)


def audit():
    source, _ = load_context(cutoff=CUTOFF)
    valid, _, _ = audited_deliveries(source)
    valid = with_context(classify(valid))
    snapshot = json.loads((ROOT / 'output/shortlist/shortlist.json').read_text(encoding='utf-8'))
    result = {'source_snapshot': snapshot['build_id'], 'status': 'Robustness diagnostics; published order unchanged',
              'categories': {}}
    for kind in ('bat', 'bowl'):
        candidates = []
        for player in snapshot['categories'][kind]['candidates']:
            frame = valid[valid[PID[kind]].eq(player['id'])].copy()
            if frame.empty:
                continue
            f = innings_stats(frame, kind).groupby('match_id')[STATS].sum()
            total = f[STATS].sum().to_numpy()
            high_matches = f[f.high_balls.gt(0)]
            if not len(high_matches) or total[0] == total[1]:
                continue
            # Remove each entire match, including both high and non-high observations.
            removals = []
            for mid, match in f.iterrows():
                rest = total - match[STATS].to_numpy()
                if rest[1] > 0 and rest[0] > rest[1]:
                    removals.append({'removed_match': int(mid), 'point': float(measures(rest)[-1])})
            baseline = float(measures(total)[-1])
            high = frame[frame[kind + '_pressure'].eq('High')].copy()
            high['value'] = high[kind + '_run_value'] + 12 * high[kind + '_wicket_value']
            by_match = high.groupby('match_id').agg(balls=('value', 'size'), value=('value', 'sum'))
            meaningful = by_match[by_match.balls.ge(3)]
            count = len(meaningful)
            positive = int(meaningful.value.gt(0).sum())
            breakdown = {}
            for dimension in ('year', 'family', 'phase', 'venue_country', 'pace_or_spin', 'batting_type', 'knock_out'):
                breakdown[dimension] = [
                    {'context': str(key), 'high_balls': len(g), 'matches': int(g.match_id.nunique()),
                     'adjusted_runs_per_six': round(float(g.value.mean()) * 6, 3),
                     'evidence': 'thin' if len(g) < 24 or g.match_id.nunique() < 4 else 'supported'}
                    for key, g in high.groupby(dimension, dropna=False)
                ]
            concentration = float(high_matches.high_balls.max() / total[1])
            removal_min = min((r['point'] for r in removals), default=None)
            candidates.append({
                'name': player['name'], 'id': player['id'], 'published_rank': player['rank'],
                'tier': player['tier'], 'high_matches': len(high_matches),
                'largest_match_share': round(concentration, 3),
                'point': baseline, 'worst_single_match_removal': removal_min,
                'single_match_swing': None if removal_min is None else baseline - removal_min,
                'positive_pressure_matches': positive, 'meaningful_pressure_matches': count,
                'smoothed_match_success': (positive + 2) / (count + 4),
                'flags': (["One match supplies over 35% of pressure balls"] if concentration > .35 else [])
                         + (["Positive impact turns negative after removing a match"] if baseline > 0 and removal_min is not None and removal_min < 0 else [])
                         + (["Fewer than four pressure matches"] if len(high_matches) < 4 else []),
                'context_breakdowns': breakdown,
            })
        result['categories'][kind] = candidates
    out = ROOT / 'output/shortlist'
    (out / 'robustness_audit.json').write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf-8')
    lines = ['# Pressure reliability: expanded evidence audit', '',
             'Uses all six source files through the validated pipeline. No extra fields are treated as score inputs merely because they exist.', '',
             'Full-match removal checks whether a player depends on one result. Context breakdowns cover season, competition, phase, venue country, pace/spin, handedness and knockouts. These small-sample slices are descriptive and do not establish causal matchup effects.', '',
             'For batting, pace/spin describes the opposing bowler; for bowling it describes the player. Handedness describes the striker in both cases.', '',
             'Match success uses at least three high-pressure balls per match and Beta(2,2) smoothing. It is a consistency diagnostic, not a match-winning probability.', '',
             'The current ranking remains historical. Existing next-season comparisons do not justify a claim of superior forecasts. New features are evidence checks rather than unvalidated score bonuses.', '']
    for kind, players in result['categories'].items():
        lines += ['## ' + ('Batters' if kind == 'bat' else 'Bowlers'), '',
                  '| Rank | Player | High matches | Largest match share | Point | Worst removal | Flags |',
                  '|---:|---|---:|---:|---:|---:|---|']
        for p in sorted((p for p in players if p['published_rank']), key=lambda p:p['published_rank']):
            worst = 'Unavailable' if p['worst_single_match_removal'] is None else f"{p['worst_single_match_removal']:+.2f}"
            lines.append(f"| {p['published_rank']} | {p['name']} | {p['high_matches']} | {p['largest_match_share']:.0%} | {p['point']:+.2f} | {worst} | {'; '.join(p['flags']) or 'No single-match flag'} |")
        lines += ['']
    lines += ['## Coverage limits', '',
              'The pack cannot recover primary extras amounts, exact running totals, reliable required run rates or win probabilities. Final results are used only for quality checks. Awards, player names and roster membership are not performance predictors. Raw files remain unchanged.', '',
              'The 20-name restriction excludes other potentially stronger players. Name collisions remain explicit: Pakistan Haider Ali is the batter; UAE Haider Ali is the bowler. Auction eligibility is unverified.']
    (out / 'Expanded_Evidence_Audit.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print('\n'.join(lines))


if __name__ == '__main__':
    audit()
