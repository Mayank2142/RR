import unittest

import pandas as pd

from backend.analytics.scoreboard import aligned_match
from scripts.scoreboard_shortlist import pressure


class ScoreboardTests(unittest.TestCase):
    def test_wides_change_score_without_using_a_legal_ball(self):
        players = {
            1: ('Aaron Alpha', 'A Alpha'), 2: ('Bryan Beta', 'B Beta'), 3: ('Charlie Gamma', 'C Gamma'),
            4: ('David Delta', 'D Delta'), 5: ('Elijah Epsilon', 'E Epsilon'), 6: ('Frank Zeta', 'F Zeta'),
        }
        local = []
        innings = []
        for inning, (team, ids) in enumerate([('A', (1, 2, 3)), ('B', (4, 5, 6))], 1):
            overs = []
            seq = 0
            for over in range(20 if inning == 1 else 1):
                balls = []
                events = ([(0, 3)] if over == 0 else []) + [(0, 0)] * 6
                if inning == 2:
                    events = [(0, 2), (2, 0)]
                for off_bat, wide in events:
                    seq += 1
                    striker, partner, bowler = ids
                    local.append({'source_row': len(local)+2, 'innings': inning, 'overid': over+1, 'runs': off_bat,
                        'innings_ball_num': seq, 'batting_team_id': inning, 'legal': not wide,
                        'extras_type': 'wide' if wide else None, 'is_wicket': False,
                        'striker_id': striker, 'striker_name': players[striker][0], 'non_striker_id': partner,
                        'non_striker_name': players[partner][0], 'bowler_id': bowler, 'bowler_name': players[bowler][0],
                        'home_team_id': 1, 'away_team_id': 2, 'home_team': 'A', 'away_team': 'B',
                        'win_team_id': 2, 'revised': False, 'unfinished': False, 'result': 'B won by 10 wickets'})
                    balls.append({'batter': players[striker][1], 'non_striker': players[partner][1],
                        'bowler': players[bowler][1], 'extras': {'wides': wide} if wide else {},
                        'runs': {'batter': off_bat, 'extras': wide, 'total': off_bat+wide}})
                overs.append({'over': over, 'deliveries': balls})
            innings.append({'team': team, 'overs': overs})
        innings[1]['target'] = {'overs': 20, 'runs': 4}
        public = {'info': {'overs': 20, 'balls_per_over': 6, 'outcome': {'winner': 'B', 'by': {'wickets': 10}},
                           'registry': {'people': {names[1]: str(pid) for pid,names in players.items()}}}, 'innings': innings}
        frame = pd.DataFrame(local)
        rows, status = aligned_match(frame, public)
        self.assertEqual(status, 'verified')
        self.assertEqual(rows[-2][1:6], (0, 0, 120, 4, 2))
        self.assertEqual(rows[-1][1:6], (2, 0, 120, 4, 0))
        frame.loc[frame.index[-1], 'runs'] = 3
        self.assertEqual(aligned_match(frame, public)[1], 'delivery_or_extras_disagreement')
        innings[1]['target']['runs'] = 5
        self.assertEqual(aligned_match(pd.DataFrame(local), public)[1], 'target_or_allocation_disagreement')

    def test_exact_chase_score_changes_pressure_and_missing_score_uses_proxy(self):
        frame = pd.DataFrame({'target': [161, 161, None], 'score_before': [141, 121, None], 'balls_left': [18, 18, None],
                              'verified_wickets_before': [2, 2, None], 'wickets_before': [2]*3, 'overid': [18]*3,
                              'striker_runs_before': [0]*3, 'partnership_runs_before': [0]*3,
                              'innings': [2]*3, 'knock_out': [0]*3})
        result = pressure(frame)
        self.assertEqual(result.bat_high_added.tolist(), [True, False, False])
        self.assertEqual(result.bowl_high_added.tolist(), [True, False, False])
        self.assertAlmostEqual(result.required_run_rate.iloc[0], 20/3)


if __name__ == '__main__':
    unittest.main()
