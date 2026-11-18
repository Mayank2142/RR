"""Publish the latest scoreboard results with the user's selection exclusions."""
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.analytics.shortlist import EXCLUDED_SELECTION_IDS, order_key, publish_local


def main():
    folder = ROOT / 'output/shortlist'
    current = json.loads((folder/'shortlist.json').read_text(encoding='utf-8'))
    source = json.loads((folder/'scoreboard_results.json').read_text(encoding='utf-8'))
    snapshot = deepcopy(current)
    snapshot.pop('build_id', None)
    snapshot['version'] = 'scoreboard-2.0-exclusion'
    snapshot['selection_policy'] = {'excluded_ids': sorted(EXCLUDED_SELECTION_IDS), 'requested_by_user': True}
    snapshot['scoreboard_audit'] = source['audit']
    snapshot['identities'] = {name: values for name, values in snapshot['identities'].items()
                              if not any(v['id'] in EXCLUDED_SELECTION_IDS for v in values)}
    for kind in ('bat', 'bowl'):
        candidates = deepcopy([p for p in source['rankings'][kind]['candidates'] if p['id'] not in EXCLUDED_SELECTION_IDS])
        candidates.sort(key=order_key)
        for p in candidates:
            p['rank'] = None
        ranking = [p for p in candidates if p['tier_code']][:10]
        for rank, p in enumerate(ranking, 1):
            p['rank'] = rank
        snapshot['categories'][kind] = {'candidates': candidates, 'ranking': ranking}
        assert len(ranking) == 10 and len({p['name'] for p in ranking}) == 10
    snapshot['audit']['accepted_legal_balls'] = source['audit']['scored_legal_balls']
    # Match and innings totals are reconstructed from the two disjoint coverage modes.
    snapshot['audit']['coverage_note'] = 'Verified full-score context plus validated proxy context for unmatched games'
    snapshot['validation']['chronological'] = {
        k: [{'scope': 'Screenshot candidates' if f['scope']=='screenshot' else 'All covered players',
             'test_year': f['year'], 'train_through': f['year']-1, 'common_players': f['players'],
             'proposed': f['scoreboard_rho'], 'legacy': f['legacy_rho']} for f in source['holdout'][k]]
        for k in ('bat', 'bowl')}
    snapshot['validation']['sensitivity'] = {}
    for k in ('bat', 'bowl'):
        base = {p['name']: p['rank'] for p in snapshot['categories'][k]['ranking']}
        rows = []
        for scenario in source['sensitivity'][k]:
            # Stored scenarios are top ten only. Exclusions can leave fewer than ten.
            names = [n for n in scenario['order'] if n in snapshot['identities']]
            ranks = {name: i+1 for i, name in enumerate(names)}
            rows.append({'scenario': scenario['scenario'], 'ranked': len(names), 'overlap': len(set(base)&set(names)),
                         'shifts': [{'player': n, 'base': r, 'scenario': ranks.get(n)} for n,r in base.items() if ranks.get(n)!=r]})
        snapshot['validation']['sensitivity'][k] = rows
    publish_local(snapshot, folder)
    (folder/'Scoreboard_Form_Selections.csv').write_bytes((folder/'Shortlist_Form_Selections.csv').read_bytes())
    for kind, side in snapshot['categories'].items():
        print(kind, [(p['rank'], p['name'], p['tier']) for p in side['ranking']])


if __name__ == '__main__':
    main()
