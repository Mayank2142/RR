"""Conservatively link local matches to public Cricsheet delivery logs."""
from collections import defaultdict
import json
from pathlib import Path
import re
import unicodedata
from zipfile import ZipFile

import numpy as np
import pandas as pd


TEAM_ALIASES = {
    'royal challengers bangalore': 'royal challengers bengaluru',
    'usa': 'united states of america',
    'united states': 'united states of america',
    'hong kong china': 'hong kong',
}
EXTRAS = {'wide': 'wides', 'Overstep': 'noballs', 'byes': 'byes', 'legbyes': 'legbyes', 'Penalty': 'penalty'}
DISMISSALS = {
    'Caught': {'caught', 'caught and bowled'}, 'Bowled': {'bowled'}, 'LBW': {'lbw'},
    'RunOut': {'run out'}, 'Stump': {'stumped'}, 'Hit Wicket': {'hit wicket'},
    'Retire Out': {'retired out'}, 'Obstracting the field': {'obstructing the field'},
    'Obstructing the field': {'obstructing the field'},
}


def words(value):
    plain = unicodedata.normalize('NFKD', str(value)).encode('ascii', 'ignore').decode()
    return re.findall(r'[a-z0-9]+', plain.casefold())


def team(value):
    name = ' '.join(words(value))
    return TEAM_ALIASES.get(name, name)


def match_key(date, sides, family):
    return str(date), tuple(sorted(map(team, sides))), family


def archive_index(paths, keys):
    index = defaultdict(list)
    for path in paths:
        family = 'IPL' if path.name == 'ipl_json.zip' else 'T20I'
        with ZipFile(path) as archive:
            for member in archive.namelist():
                if not member.endswith('.json'):
                    continue
                doc = json.loads(archive.read(member))
                info = doc['info']
                if info['gender'] != 'male':
                    continue
                key = match_key(info['dates'][0], info['teams'], family)
                if key in keys:
                    index[key].append((Path(member).stem, doc))
    return index


def aligned_match(local, doc):
    """Accept a complete regular match only when the delivery stream and score reconcile."""
    info = doc['info']
    outcome = info['outcome']
    innings = [inn for inn in doc['innings'] if not inn.get('super_over', False)]
    if info['overs'] != 20 or info['balls_per_over'] != 6 or outcome.get('method') or len(innings) != 2:
        return None, 'revised_or_incomplete_public_match'
    if 'winner' not in outcome and outcome.get('result') != 'tie':
        return None, 'unfinished_public_match'
    if any(inn.get('penalty_runs') or inn.get('miscounted_overs') or inn.get('absent_hurt') for inn in innings):
        return None, 'special_innings_conditions'
    if local.revised.any() or local.unfinished.any() or local.result.str.contains(r'\bD\s*/\s*L\b|\bDLS\b|Duckworth', case=False, na=False).any():
        return None, 'revised_or_incomplete_local_match'
    local = local[local.innings.isin([1, 2])]
    local_teams = dict(zip([local.home_team_id.iat[0], local.away_team_id.iat[0]],
                           [team(local.home_team.iat[0]), team(local.away_team.iat[0])]))
    winner = local.win_team_id.iat[0]
    if winner in local_teams and 'winner' in outcome and local_teams[winner] != team(outcome['winner']):
        return None, 'winner_disagreement'
    registry = info['registry']['people']
    forward, reverse = {}, {}
    names_ok = set()
    rows = []
    first_total = target = None
    for number, inn in enumerate(innings, 1):
        group = local[local.innings.eq(number)]
        public = [(over['over']+1, ball) for over in inn['overs'] for ball in over['deliveries']]
        if len(group) != len(public) or not public or not np.array_equal(group.innings_ball_num, np.arange(1, len(group)+1)):
            return None, 'delivery_count_or_sequence_disagreement'
        if set(group.batting_team_id.map(local_teams)) != {team(inn['team'])}:
            return None, 'batting_team_disagreement'
        if number == 2:
            chase = inn.get('target', {})
            target = chase.get('runs', first_total+1)
            if chase.get('overs', 20) != 20 or target != first_total+1:
                return None, 'target_or_allocation_disagreement'
        score = wickets = legal = 0
        for source, (over, ball) in zip(group.itertuples(index=False), public):
            runs = ball['runs']
            extras = ball.get('extras', {})
            charged = extras.get('wides', 0)+extras.get('noballs', 0)
            is_legal = charged == 0
            expected_extra = EXTRAS.get(source.extras_type)
            if (source.overid != over or source.runs != runs['batter'] or sum(extras.values()) != runs['extras']
                    or runs['batter'] + runs['extras'] != runs['total']
                    or (expected_extra and expected_extra not in extras)
                    or (source.extras_type != 'other' and is_legal != source.legal)):
                return None, 'delivery_or_extras_disagreement'
            dismissal = [event for event in ball.get('wickets', []) if event['kind'] != 'retired hurt']
            if bool(source.is_wicket) != bool(dismissal) or len(dismissal) > 1:
                return None, 'wicket_disagreement'
            if dismissal and dismissal[0]['kind'] not in DISMISSALS.get(source.dismissal_type, ()):
                return None, 'wicket_type_disagreement'
            for id_field, name_field, public_field in [('striker_id','striker_name','batter'),
                                                       ('non_striker_id','non_striker_name','non_striker'),
                                                       ('bowler_id','bowler_name','bowler')]:
                pid = getattr(source, id_field)
                public_name = ball[public_field]
                public_id = registry[public_name]
                if forward.setdefault(pid, public_id) != public_id or reverse.setdefault(public_id, pid) != pid:
                    return None, 'player_sequence_disagreement'
                if set(words(getattr(source, name_field))) & {word for word in words(public_name) if len(word) >= 3}:
                    names_ok.add(pid)
            if dismissal and registry[dismissal[0]['player_out']] != forward.get(source.dismissed_player_id):
                return None, 'dismissed_player_disagreement'
            # The observed scoreboard stops immediately before this event.
            rows.append((source.source_row, score, wickets, 120-legal, target if number == 2 else None,
                         int(runs['extras']), int(charged), int(runs['total']), is_legal))
            score += runs['total']
            wickets += len(dismissal)
            legal += is_legal
        if legal > 120 or wickets > 10 or (number == 1 and legal != 120 and wickets != 10):
            return None, 'incomplete_allocation'
        if number == 1:
            first_total = score
        else:
            margin = outcome.get('by', {})
            if ('runs' in margin and first_total - score != margin['runs']) or (
                    'wickets' in margin and (score < target or 10-wickets != margin['wickets'])) or (
                    outcome.get('result') == 'tie' and score != first_total):
                return None, 'scorecard_margin_disagreement'
    if len(names_ok) < .75*len(forward):
        return None, 'too_few_player_names_corroborated'
    return rows, 'verified'


def recover(base, paths):
    groups = list(base.groupby('match_id', sort=False))
    lookup = {mid: match_key(g.match_date.iat[0], (g.home_team.iat[0], g.away_team.iat[0]), g.family.iat[0])
              for mid,g in groups}
    index = archive_index(paths, set(lookup.values()))
    events, audit = [], []
    for mid, group in groups:
        key = lookup[mid]
        found, statuses = [], []
        for public_id, doc in index.get(key, []):
            rows, status = aligned_match(group, doc)
            statuses.append(status)
            if rows is not None:
                found.append((public_id, rows))
        audit.append({'match_id': int(mid), 'family': key[2], 'date': key[0],
                      'public_candidates': len(statuses), 'reason': ('verified' if len(found) == 1 else
                         'ambiguous' if len(found) > 1 else '|'.join(sorted(set(statuses))) or 'no_public_date_team_match'),
                      'cricsheet_id': found[0][0] if len(found) == 1 else None})
        if len(found) == 1:
            events.extend(found[0][1])
    crosswalk = pd.DataFrame(audit)
    if crosswalk.cricsheet_id.dropna().duplicated().any():
        raise ValueError('A public match maps to more than one local match')
    state = pd.DataFrame(events, columns=['source_row','score_before','verified_wickets_before','balls_left','target',
                                          'verified_extras','charged_extras','total_runs','verified_legal'])
    return state, crosswalk
