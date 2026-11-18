"""Chronological model-selection experiment. Never overwrites published rankings."""
from pathlib import Path
import sys
import json
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.analytics.shortlist import (
    CUTOFF, PID, STATS, POOL, load_context, audited_deliveries, classify,
    PeerExpectations, innings_stats, measured_role, evidence_tier, estimates,
)

MODELS = ('published', 'usual', 'pressure', 'pooled', 'recent_pooled')
SEED = 20261117


def predictions(matches, kind, pid, dates, asof):
    """Shrink pressured quality toward usual ability; no lift bonus for a weak baseline."""
    sums = matches[STATS].sum()
    usual = (sums.quality - sums.high_quality) / (sums.balls - sums.high_balls + 120)
    pooled = (sums.high_quality + 120 * usual) / (sums.high_balls + 120)
    ages = (pd.Timestamp(asof) - pd.to_datetime(dates.reindex(matches.index))).dt.days
    if ages.isna().any() or ages.lt(0).any():
        raise ValueError('Training matches must have known dates before the cutoff')
    # Two-year half-life declared before running comparisons. Weighted exposure remains explicit.
    weights = np.exp2(-ages.to_numpy() / 730)
    weighted = matches[STATS].mul(weights, axis=0).sum()
    ru = (weighted.quality - weighted.high_quality) / (weighted.balls - weighted.high_balls + 120)
    rp = (weighted.high_quality + 120 * ru) / (weighted.high_balls + 120)
    old = estimates(matches, kind, pid)
    return {'published': old['score'], 'usual': float(6 * usual),
            'pressure': float(6 * sums.high_quality / (sums.high_balls + 60)),
            'pooled': float(6 * pooled), 'recent_pooled': float(6 * rp)}


def correlation(rows, model):
    if len(rows) < 5:
        return None
    x, y = [r[model] for r in rows], [r['observed'] for r in rows]
    if len(set(x)) < 2 or len(set(y)) < 2:
        return None
    return float(spearmanr(x, y).statistic)


def nested_evaluation(folds):
    """Select on earlier validation years only; compare on the next year."""
    evaluated = []
    for year in (2025, 2026):
        previous = [rows for y, rows in folds.items() if y < year]
        averages = {m: float(np.mean([correlation(r, m) for r in previous])) for m in MODELS}
        selected = max(MODELS, key=lambda m: averages[m])
        baseline = max(('published', 'usual', 'pressure'), key=lambda m: averages[m])
        rows = folds[year]
        evaluated.append({'year': year, 'chosen_before_year': selected, 'baseline_before_year': baseline,
                          'n': len(rows), 'selected_rho': correlation(rows, selected),
                          'baseline_rho': correlation(rows, baseline), 'training_validation_means': averages})
    # Cluster resample player IDs jointly across years, preserving repeat-player dependence.
    ids = sorted({r['id'] for year in (2025, 2026) for r in folds[year]})
    lookup = {year: {r['id']: r for r in folds[year]} for year in (2025, 2026)}
    rng = np.random.default_rng(SEED)
    differences = []
    for _ in range(1000):
        draw = rng.choice(ids, size=len(ids), replace=True)
        by_year = []
        for test in evaluated:
            subset = [lookup[test['year']][pid] for pid in draw if pid in lookup[test['year']]]
            x = correlation(subset, test['chosen_before_year'])
            y = correlation(subset, test['baseline_before_year'])
            if x is not None and y is not None:
                by_year.append(x-y)
        if len(by_year) == 2:
            differences.append(float(np.mean(by_year)))
    ci = np.quantile(differences, [.025, .975]).tolist()
    delta = float(np.mean([r['selected_rho']-r['baseline_rho'] for r in evaluated]))
    # This is retrospective evidence; prospective validation is still required even if it passes.
    passed = ci[0] > 0 and all(r['selected_rho'] >= r['baseline_rho'] for r in evaluated)
    return {'folds': evaluated, 'mean_gain': delta, 'paired_player_bootstrap_95': ci,
            'screen_passed': bool(passed), 'bootstrap_draws': len(differences)}


def main():
    raw, _ = load_context(cutoff=CUTOFF)
    valid, _, _ = audited_deliveries(raw)
    valid = classify(valid)
    dates = valid.groupby('match_id').match_date.first()
    result = {'design': 'Earlier-year validation chooses model; later-year evaluation uses common eligible players.',
              'scope': 'Retrospective model development. All supplied years have previously been inspected.',
              'target': 'Next-year context-adjusted high-pressure run equivalents per six legal balls',
              'promotion_rule': 'Positive lower paired-bootstrap gain bound and no fold worse than the earlier-selected simple baseline; prospective confirmation still required.',
              'categories': {}}
    for kind in ('bat', 'bowl'):
        folds = {}
        for year in (2024, 2025, 2026):
            train, test = valid[valid.year.lt(year)], valid[valid.year.eq(year)]
            assert not set(train.match_id) & set(test.match_id)
            context = PeerExpectations(train, kind)
            def make(frame):
                frame = frame.copy()
                frame[kind+'_run_value'], frame[kind+'_wicket_value'] = context.residuals(frame, kind)
                return innings_stats(frame, kind)
            past, future = make(train), make(test)
            future_groups = {pid:g for pid,g in future.groupby('player_id')
                             if g.high_balls.sum() >= 24 and g[g.high_balls.gt(0)].match_id.nunique() >= 3}
            players = {pid:g for pid,g in train.groupby(PID[kind])}
            rows = []
            for pid, innings in past[past.player_id.isin(future_groups)].groupby('player_id'):
                matches = innings.groupby('match_id')[STATS].sum()
                role_ok, _, _ = measured_role(kind, players[pid], innings)
                tier, _ = evidence_tier(kind, role_ok, innings.sum(numeric_only=True), len(innings),
                                       int(innings.high_balls.gt(0).sum()), int(matches.high_balls.gt(0).sum()))
                if tier < 2:
                    continue
                observed = future_groups[pid]
                rows.append({'id': int(pid), **predictions(matches, kind, pid, dates, f'{year}-01-01'),
                             'observed': float(6 * observed.high_quality.sum() / observed.high_balls.sum())})
            folds[year] = rows
        allow = {p.player_id(kind) for p in POOL}
        result['categories'][kind] = {
            'all_players': {year: {'n':len(rows), **{m:correlation(rows,m) for m in MODELS}} for year,rows in folds.items()},
            'screenshot_players': {year: {'n':sum(r['id'] in allow for r in rows),
                                   **{m:correlation([r for r in rows if r['id'] in allow],m) for m in MODELS}}
                                   for year,rows in folds.items()},
            'nested': nested_evaluation(folds), 'evaluation_rows': folds,
        }
    out = ROOT/'output/shortlist'
    (out/'model_comparison.json').write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf-8')
    lines = ['# Stronger approach: test before changing ranks', '',
             'The experiment compares five methods on common players: the published conservative score, usual ability, pressure-only ability, pressure ability shrunk toward usual performance, and the pooled method with a two-year recency half-life.', '',
             'Pooling removes the bonus a weak usual baseline can give the old lift term. Recency is a candidate assumption, not an automatic improvement. Existing peer expectations exclude the player and are fitted only on preceding years.', '',
             'Method selection uses earlier validation years. The 2025 and 2026 evaluation compares with the best simple baseline selected from earlier years. A paired player-cluster bootstrap measures uncertainty in the average correlation gain. All years have already been inspected in this project, so this is retrospective evidence, not a pristine final test.', '']
    for kind, data in result['categories'].items():
        lines += ['## '+kind, '', '| Test year | Players | Published | Usual | Pressure | Pooled | Recent pooled |',
                  '|---|---:|---:|---:|---:|---:|---:|']
        for year,row in data['all_players'].items():
            lines.append('| '+str(year)+' | '+str(row['n'])+' | '+' | '.join(f'{row[m]:+.3f}' for m in MODELS)+' |')
        n=data['nested']
        lines += ['', f"Nested mean gain: {n['mean_gain']:+.3f}; paired 95% interval: {n['paired_player_bootstrap_95'][0]:+.3f} to {n['paired_player_bootstrap_95'][1]:+.3f}.",
                  'Promotion screen: '+('passed retrospectively; prospective confirmation required' if n['screen_passed'] else 'not passed; retain the published descriptive ranking'), '']
        for f in n['folds']:
            lines.append(f"- {f['year']}: earlier data selected {f['chosen_before_year']}; baseline {f['baseline_before_year']}.")
    lines += ['', '## Next decision', '',
              'Do not combine highly correlated features into extra score bonuses. Keep context slices and single-match removal as diagnostic evidence. Expand only with verified scoreboard/extras data and more repeated pressure matches; never infer missing required run rates or availability. The 20-name screenshot pool remains the output constraint.', '',
              'The primary historical submission measures pressure performance and change versus usual performance. A model predicting later performance is a separate research question; even a forecasting winner cannot silently redefine that submission objective.']
    (out/'Model_Improvement_Results.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
