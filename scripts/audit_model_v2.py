"""Read-only diagnostics for the v2 implementation plan. Does not rerank players."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.analytics.context import load_context


def main():
    snapshot_path = ROOT / 'output' / 'analysis.json'
    before = hashlib.sha256(snapshot_path.read_bytes()).hexdigest()
    snapshot = json.loads(snapshot_path.read_text(encoding='utf-8'))
    source, audit = load_context()
    valid = source[source.eligible_context]
    innings = valid.groupby(['match_id', 'innings']).agg(
        last_over=('overid', 'max'), wickets=('is_wicket', 'sum'),
        batting_team=('batting_team_id', 'first'), winner=('win_team_id', 'first'),
        result=('result', 'first'), legal_balls=('legal', 'sum'), date=('match_date', 'first'),
    )
    # Diagnostic only: retired-hurt endings and legitimately reduced matches can be valid.
    # Never infer allocated overs from the last observed delivery or reject these automatically.
    flagged = innings[
        (innings.last_over < 20) & (innings.wickets < 10)
        & ((innings.index.get_level_values('innings') == 1) | (innings.batting_team != innings.winner))
    ].reset_index()
    flagged = flagged.astype(object).where(flagged.notna(), None)
    categories = {}
    for kind in ['bat', 'bowl']:
        players = snapshot['rankings'][kind]
        validation = snapshot['validation'][kind]
        categories[kind] = {
            'eligible_players': len(players),
            'holdout': validation['chronological_holdout'],
            'pressure_rule_top10_overlap': {
                test['scenario']: test['top10_overlap']
                for test in validation['threshold_tests'][:2]
            },
            'ipl_only_top10_overlap': validation['ipl_only']['top10_overlap'],
            'eligible_role_counts': dict(Counter(p['role'] for p in players)),
            'top10_role_counts': dict(Counter(p['role'] for p in players[:10])),
            'top10_samples': [
                {'name': p['name'], 'high_legal_balls': p['metrics']['high_balls'],
                 'high_innings': p['metrics']['high_innings'],
                 'conditional_score_interval': [p['score_low'], p['score_high']],
                 'top10_weight_scenario_frequency': p['stability']['top10_weight_frequency']}
                for p in players[:10]
            ],
        }
    result = {
        'kind': 'planning_audit_only', 'prepared_on': '2026-11-11',
        'analysis_sha256': before, 'source_model_version': snapshot['methodology']['version'],
        'local_only': True, 'categories': categories,
        'innings_requiring_end_or_allocation_review': {
            'count': len(flagged),
            'meaning': 'Review flags, not proof of truncation or invalidity. Check allocated overs, rain, retirements and scorecards.',
            'examples': flagged.to_dict('records'),
        },
        'implementation_findings': [
            'Pressure definitions omit target and exact scoreboard because primary extras are missing.',
            'Revision detection only checks non-null numeric revision fields. Some retained result descriptions explicitly contain D/L.',
            'Phase boundaries assume a 20-over allocation. A correctly shortened innings needs verified allocation-specific phase handling.',
            'Context cell expectations contain the scored player in descriptive mode. V2 needs cross-fitted expectations for historical assessment and fitted-then-applied expectations for forecasting.',
            'The wicket cost, component weights, priors and confidence bonus are assumptions rather than independently validated player-selection rules.',
            'Current per-player bootstrap freezes expectations, normalization and eligibility. It is not a joint posterior probability of top-10 membership.',
            'Backtest eligibility uses a hardcoded 2025 activity gate with training years overwritten to bypass it. Replace with an explicit as-of date.',
            '2025-2026 results have already been examined. They cannot become a pristine unseen test by relabeling the split.',
        ],
    }
    assert hashlib.sha256(snapshot_path.read_bytes()).hexdigest() == before
    out = ROOT / 'output' / 'model_v2_audit.json'
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    print(json.dumps({'audit_file': str(out), 'flagged_innings': len(flagged),
                      'v1_rankings_unchanged': True,
                      'batting_holdout_spearman': categories['bat']['holdout']['spearman'],
                      'bowling_holdout_spearman': categories['bowl']['holdout']['spearman']}, indent=2))


if __name__ == '__main__':
    main()
