# Supplied data inventory

All original files are unchanged. No Excel workbooks were supplied.

| File | Rows | Fields | Exact duplicate rows |
|---|---:|---:|---:|
| ball_by_ball.csv | 200999 | 33 | 0 |
| competition_team_player_mapping.csv | 6413 | 6 | 0 |
| competitions.csv | 141 | 4 | 0 |
| matches.csv | 883 | 22 | 0 |
| playing_eleven.csv | 28381 | 9 | 0 |
| Round 1 Problem Statement _ SupeRR Selector Season 2.docx.pdf | PDF | - | - |
| teams.csv | 353 | 3 | 0 |

## Field dictionary

### ball_by_ball.csv

| Field | Type | Missing | Meaning |
|---|---|---:|---|
| match_id | int64 | 0 | Match join key. Unique in matches, repeated for deliveries and XIs. |
| innings | int64 | 0 | Innings number; 3/4 are super overs and excluded from main model. |
| overid | int64 | 0 | One-based over index (1-20). Defines phase, not legal balls elapsed. |
| over_ball_num | int64 | 0 | Sequential delivery within over including illegal deliveries. |
| innings_ball_num | int64 | 0 | Sequential delivery event within innings, including illegal balls. |
| batting_team_id | int64 | 0 | Descriptive source field; not a direct score input. |
| bowling_team_id | int64 | 0 | Descriptive source field; not a direct score input. |
| striker_id | int64 | 0 | Canonical striker identity. Join by ID, never fuzzy names. |
| striker_name | str | 0 | Descriptive source field; not a direct score input. |
| non_striker_id | int64 | 0 | Canonical non-striker identity. |
| non_striker_name | str | 0 | Descriptive source field; not a direct score input. |
| bowler_id | int64 | 0 | Canonical bowler identity. |
| bowler_name | str | 0 | Descriptive source field; not a direct score input. |
| batting_type | str | 0 | Batting handedness, descriptive. |
| bowling_type | str | 0 | Bowling style, descriptive and role grouping. |
| batting_order | int64 | 0 | Recorded batting position. Used for descriptive role grouping. |
| runs | int64 | 0 | Recorded off-bat runs. Extras are not included. Not team runs. |
| is_four | bool | 0 | Boundary flag, checked against runs; mismatches flagged. |
| is_six | bool | 0 | Boundary flag, checked against runs; mismatches flagged. |
| is_wicket | bool | 0 | Wicket event; distinguish team wickets, striker dismissal and bowler credit. |
| dismissal_type_id | float64 | 190118 | Descriptive source field; not a direct score input. |
| dismissal_type | str | 190118 | Dismissal description. RunOut/retire/obstruction not credited to bowler. |
| dismissed_player_id | float64 | 190107 | Actual dismissed batter ID; may be non-striker. |
| extras_type | str | 189167 | Extra category; Overstep treated as known no-ball. Other remains ambiguous. |
| extras1_runs | int64 | 0 | MISLABELLED category code: 1 Overstep, 2 wide, 3 legbyes, 4 byes, 5 other, 6 none, 7 Penalty. Never sum as runs. |
| extras_2_runs | int64 | 0 | Sparse secondary extras value. Cannot restore missing primary extras quantities. |
| pace_or_spin | str | 0 | Bowling family, used for style-split summaries. |
| bowl_speed | float64 | 0 | Recorded speed; zeros/coverage inspected, not used in scoring. |
| stroke | str | 6158 | Descriptive source field; not a direct score input. |
| delivery_style | str | 391 | Descriptive source field; not a direct score input. |
| over_or_around | str | 407 | Descriptive source field; not a direct score input. |
| on_or_off | str | 0 | Descriptive source field; not a direct score input. |
| delivery_ist_time | str | 0 | Mostly date-level timestamps; not used as chronological ball ordering. |

### competition_team_player_mapping.csv

| Field | Type | Missing | Meaning |
|---|---|---:|---|
| comp_id | int64 | 0 | Competition join key, with format and season in competitions. |
| comp_name | str | 0 | Descriptive source field; not a direct score input. |
| team_id | int64 | 0 | Descriptive source field; not a direct score input. |
| team_name | str | 0 | Descriptive source field; not a direct score input. |
| player_id | int64 | 0 | Canonical player identity in roster sources. |
| player_name | str | 0 | Source display name. Dropdown spelling not verified from live form. |

### competitions.csv

| Field | Type | Missing | Meaning |
|---|---|---:|---|
| comp_id | int64 | 0 | Competition join key, with format and season in competitions. |
| comp_name | str | 0 | Descriptive source field; not a direct score input. |
| match_format | str | 0 | Descriptive source field; not a direct score input. |
| season | str | 0 | Descriptive source field; not a direct score input. |

### matches.csv

| Field | Type | Missing | Meaning |
|---|---|---:|---|
| match_id | int64 | 0 | Match join key. Unique in matches, repeated for deliveries and XIs. |
| comp_id | int64 | 0 | Competition join key, with format and season in competitions. |
| match_number | int64 | 0 | Descriptive source field; not a direct score input. |
| match_date | str | 0 | Match date and analytical cutoff, not delivery_ist_time. |
| stage | str | 0 | Descriptive source field; not a direct score input. |
| venue_id | int64 | 0 | Descriptive source field; not a direct score input. |
| venue_country | str | 0 | Descriptive source field; not a direct score input. |
| home_team_id | int64 | 0 | Descriptive source field; not a direct score input. |
| home_team | str | 0 | Descriptive source field; not a direct score input. |
| away_team_id | int64 | 0 | Descriptive source field; not a direct score input. |
| away_team | str | 0 | Descriptive source field; not a direct score input. |
| home_team_captain_id | float64 | 44 | Descriptive source field; not a direct score input. |
| away_team_captain_id | float64 | 45 | Descriptive source field; not a direct score input. |
| toss_win_team_id | float64 | 15 | Descriptive source field; not a direct score input. |
| toss_opted | str | 15 | Descriptive source field; not a direct score input. |
| man_of_the_match | int64 | 0 | Descriptive source field; not a direct score input. |
| first_inn_revised_overs | float64 | 858 | Observed values 30-114 indicate revised legal-ball allocation despite label. Exclude revised games in primary model. |
| second_inn_revised_overs | float64 | 858 | Observed values 30-114 indicate revised legal-ball allocation despite label. Exclude revised games in primary model. |
| revised_target | float64 | 860 | Revised chase target where provided; insufficient for all chases. |
| knock_out | int64 | 0 | Pre-match knockout indicator, used in pressure rules. |
| win_team_id | float64 | 41 | Result team. Used only in descriptive outcome summaries, not pressure labels. |
| result | str | 0 | Final result text. Never used to label pre-delivery pressure. |

### playing_eleven.csv

| Field | Type | Missing | Meaning |
|---|---|---:|---|
| match_id | int64 | 0 | Match join key. Unique in matches, repeated for deliveries and XIs. |
| team_id | int64 | 0 | Descriptive source field; not a direct score input. |
| player_id | int64 | 0 | Canonical player identity in roster sources. |
| batting_order | float64 | 8678 | Recorded batting position. Used for descriptive role grouping. |
| is_played | bool | 0 | Descriptive source field; not a direct score input. |
| is_captain | object | 8667 | Descriptive source field; not a direct score input. |
| is_wk | object | 8667 | Descriptive source field; not a direct score input. |
| is_impact | int64 | 0 | Descriptive source field; not a direct score input. |
| is_impact_off | int64 | 0 | Descriptive source field; not a direct score input. |

### teams.csv

| Field | Type | Missing | Meaning |
|---|---|---:|---|
| comp_id | int64 | 0 | Competition join key, with format and season in competitions. |
| team_id | int64 | 0 | Descriptive source field; not a direct score input. |
| team_name | str | 0 | Descriptive source field; not a direct score input. |

## Integrity findings

```json
{
  "delivery_rows": 200999,
  "matches_with_deliveries": 867,
  "match_metadata_rows": 883,
  "metadata_without_deliveries": [
    31281,
    31284,
    31288,
    32610,
    32612,
    32622,
    36210,
    36564,
    38797,
    40761,
    41502,
    41503,
    42030,
    46008,
    48513,
    50189
  ],
  "orphan_delivery_matches": [],
  "orphan_match_competitions": [],
  "duplicate_delivery_event_keys": 0,
  "duplicate_match_keys": 0,
  "date_min": "2022-01-22",
  "date_max": "2026-11-01",
  "extra_code_cross_tab": {
    "Overstep": {
      "1": 576,
      "2": 0,
      "3": 0,
      "4": 0,
      "5": 0,
      "6": 0,
      "7": 0
    },
    "Penalty": {
      "1": 0,
      "2": 0,
      "3": 0,
      "4": 0,
      "5": 0,
      "6": 0,
      "7": 1
    },
    "byes": {
      "1": 0,
      "2": 0,
      "3": 0,
      "4": 529,
      "5": 0,
      "6": 0,
      "7": 0
    },
    "legbyes": {
      "1": 0,
      "2": 0,
      "3": 2748,
      "4": 0,
      "5": 0,
      "6": 0,
      "7": 0
    },
    "none": {
      "1": 0,
      "2": 0,
      "3": 0,
      "4": 0,
      "5": 0,
      "6": 189167,
      "7": 0
    },
    "other": {
      "1": 0,
      "2": 0,
      "3": 0,
      "4": 0,
      "5": 264,
      "6": 0,
      "7": 0
    },
    "wide": {
      "1": 0,
      "2": 7714,
      "3": 0,
      "4": 0,
      "5": 0,
      "6": 0,
      "7": 0
    }
  },
  "ambiguous_other_rows": 264,
  "boundary_flag_mismatches": 23,
  "nonpositive_speed_rows": 77862,
  "super_over_rows": 38,
  "revised_match_rows": 34,
  "player_ids_with_multiple_names": {},
  "names_with_multiple_ids": {
    "Abdul Samad": [
      7446,
      6922
    ],
    "Bashir Ahmad": [
      39479,
      29833
    ],
    "Basil Hameed": [
      8638,
      39444
    ],
    "Haider Ali": [
      7338,
      28756
    ],
    "Mohammad Ali": [
      3083,
      20229
    ],
    "Muhammad Farooq": [
      27373,
      28978
    ],
    "Rashid Khan": [
      4722,
      20172
    ]
  },
  "formats": {
    "T20I": 134,
    "T20": 7
  },
  "seasons": {
    "2024": 33,
    "2025": 33,
    "2026": 25,
    "2022": 25,
    "2023": 20,
    "2022/23": 3,
    "2023/24": 1,
    "2024/25": 1
  }
}
```

## Available context and missing inputs

Available: pre-ball wickets, over phase, batter off-bat runs, partnership off-bat runs, knockout stage, player identities, result and seasons.
Unavailable: reliable primary extras amounts, exact score/target/RRR for every chase, complete economy, costs, age, nationality, injuries and 2027 auction availability.
Do not sum extras1_runs, use final results to label pressure, or silently replace missing extras with one run.