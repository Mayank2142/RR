"""Read every supplied structured source without modifying it."""
from pathlib import Path
import hashlib
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / '6af3166e7b922_data_pack'
OUT = ROOT / 'output'

MEANINGS = {
    'match_id': 'Match join key. Unique in matches, repeated for deliveries and XIs.',
    'comp_id': 'Competition join key, with format and season in competitions.',
    'innings': 'Innings number; 3/4 are super overs and excluded from main model.',
    'overid': 'One-based over index (1-20). Defines phase, not legal balls elapsed.',
    'over_ball_num': 'Sequential delivery within over including illegal deliveries.',
    'innings_ball_num': 'Sequential delivery event within innings, including illegal balls.',
    'runs': 'Recorded off-bat runs. Extras are not included. Not team runs.',
    'extras1_runs': 'MISLABELLED category code: 1 Overstep, 2 wide, 3 legbyes, 4 byes, 5 other, 6 none, 7 Penalty. Never sum as runs.',
    'extras_2_runs': 'Sparse secondary extras value. Cannot restore missing primary extras quantities.',
    'extras_type': 'Extra category; Overstep treated as known no-ball. Other remains ambiguous.',
    'is_wicket': 'Wicket event; distinguish team wickets, striker dismissal and bowler credit.',
    'dismissal_type': 'Dismissal description. RunOut/retire/obstruction not credited to bowler.',
    'dismissed_player_id': 'Actual dismissed batter ID; may be non-striker.',
    'is_four': 'Boundary flag, checked against runs; mismatches flagged.',
    'is_six': 'Boundary flag, checked against runs; mismatches flagged.',
    'striker_id': 'Canonical striker identity. Join by ID, never fuzzy names.',
    'non_striker_id': 'Canonical non-striker identity.',
    'bowler_id': 'Canonical bowler identity.',
    'player_id': 'Canonical player identity in roster sources.',
    'player_name': 'Source display name. Dropdown spelling not verified from live form.',
    'batting_order': 'Recorded batting position. Used for descriptive role grouping.',
    'batting_type': 'Batting handedness, descriptive.',
    'bowling_type': 'Bowling style, descriptive and role grouping.',
    'pace_or_spin': 'Bowling family, used for style-split summaries.',
    'bowl_speed': 'Recorded speed; zeros/coverage inspected, not used in scoring.',
    'first_inn_revised_overs': 'Observed values 30-114 indicate revised legal-ball allocation despite label. Exclude revised games in primary model.',
    'second_inn_revised_overs': 'Observed values 30-114 indicate revised legal-ball allocation despite label. Exclude revised games in primary model.',
    'revised_target': 'Revised chase target where provided; insufficient for all chases.',
    'win_team_id': 'Result team. Used only in descriptive outcome summaries, not pressure labels.',
    'result': 'Final result text. Never used to label pre-delivery pressure.',
    'knock_out': 'Pre-match knockout indicator, used in pressure rules.',
    'match_date': 'Match date and analytical cutoff, not delivery_ist_time.',
    'delivery_ist_time': 'Mostly date-level timestamps; not used as chronological ball ordering.',
}

def main():
    OUT.mkdir(exist_ok=True)
    inventory = []
    tables = {}
    for p in sorted(RAW.rglob('*')):
        if not p.is_file():
            continue
        base = {'file': str(p.relative_to(ROOT)), 'bytes': p.stat().st_size,
                'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
        if p.suffix.lower() == '.csv':
            d = pd.read_csv(p, low_memory=False)
            tables[p.stem] = d
            base.update(rows=len(d), columns=len(d.columns), exact_duplicate_rows=int(d.duplicated().sum()),
                        fields=[{'name': c, 'dtype': str(d[c].dtype), 'nulls': int(d[c].isna().sum()),
                                 'distinct': int(d[c].nunique()),
                                 'examples': [str(v) for v in d[c].dropna().unique()[:6]],
                                 'meaning': MEANINGS.get(c, 'Descriptive source field; not a direct score input.')}
                                for c in d.columns])
        elif p.suffix.lower() in {'.xlsx', '.xls'}:
            # There are no workbooks in the supplied pack; future packs inspect all sheets.
            book = pd.ExcelFile(p)
            base['worksheets'] = [{'name': s, 'rows': len(pd.read_excel(book, sheet_name=s)),
                                   'columns': list(pd.read_excel(book, sheet_name=s, nrows=0).columns)} for s in book.sheet_names]
        else:
            base['kind'] = 'Official problem-statement PDF' if p.suffix.lower() == '.pdf' else 'Other file'
        inventory.append(base)
    b, m, c = tables['ball_by_ball'], tables['matches'], tables['competitions']
    p = tables['competition_team_player_mapping']
    checks = {
        'delivery_rows': len(b), 'matches_with_deliveries': int(b.match_id.nunique()),
        'match_metadata_rows': len(m), 'metadata_without_deliveries': sorted(set(m.match_id)-set(b.match_id)),
        'orphan_delivery_matches': sorted(set(b.match_id)-set(m.match_id)),
        'orphan_match_competitions': sorted(set(m.comp_id)-set(c.comp_id)),
        'duplicate_delivery_event_keys': int(b.duplicated(['match_id','innings','innings_ball_num']).sum()),
        'duplicate_match_keys': int(m.match_id.duplicated().sum()),
        'date_min': m.match_date.min(), 'date_max': m.match_date.max(),
        'extra_code_cross_tab': pd.crosstab(b.extras1_runs, b.extras_type.fillna('none')).to_dict(),
        'ambiguous_other_rows': int(b.extras_type.eq('other').sum()),
        'boundary_flag_mismatches': int(((b.runs.eq(4)!=b.is_four)|(b.runs.eq(6)!=b.is_six)).sum()),
        'nonpositive_speed_rows': int(b.bowl_speed.le(0).sum()),
        'super_over_rows': int(b.innings.gt(2).sum()),
        'revised_match_rows': int(m[['first_inn_revised_overs','second_inn_revised_overs','revised_target']].notna().any(axis=1).sum()),
        'player_ids_with_multiple_names': {str(k): list(v) for k,v in p.groupby('player_id').player_name.unique().items() if len(v)>1},
        'names_with_multiple_ids': {str(k): [int(x) for x in v] for k,v in p.groupby('player_name').player_id.unique().items() if len(v)>1},
        'formats': c.match_format.value_counts().to_dict(),
        'seasons': c.season.astype(str).value_counts().to_dict(),
    }
    (OUT/'dataset_inventory.json').write_text(json.dumps({'files': inventory, 'checks': checks}, indent=2, default=str), encoding='utf-8')
    lines = ['# Supplied data inventory', '', 'All original files are unchanged. No Excel workbooks were supplied.', '',
             '| File | Rows | Fields | Exact duplicate rows |', '|---|---:|---:|---:|']
    for f in inventory:
        lines.append(f"| {Path(f['file']).name} | {f.get('rows','PDF')} | {f.get('columns','-')} | {f.get('exact_duplicate_rows','-')} |")
    lines += ['', '## Field dictionary']
    for f in inventory:
        if 'fields' not in f: continue
        lines += ['', '### '+Path(f['file']).name, '', '| Field | Type | Missing | Meaning |', '|---|---|---:|---|']
        for x in f['fields']:
            lines.append(f"| {x['name']} | {x['dtype']} | {x['nulls']} | {x['meaning']} |")
    lines += ['', '## Integrity findings', '', '```json', json.dumps(checks, indent=2, default=str), '```', '',
              '## Available context and missing inputs', '',
              'Available: pre-ball wickets, over phase, batter off-bat runs, partnership off-bat runs, knockout stage, player identities, result and seasons.',
              'Unavailable: reliable primary extras amounts, exact score/target/RRR for every chase, complete economy, costs, age, nationality, injuries and 2027 auction availability.',
              'Do not sum extras1_runs, use final results to label pressure, or silently replace missing extras with one run.']
    (OUT/'data_dictionary.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps({k:v for k,v in checks.items() if k not in ['extra_code_cross_tab','player_ids_with_multiple_names','names_with_multiple_ids','metadata_without_deliveries']}, indent=2))

if __name__ == '__main__': main()
