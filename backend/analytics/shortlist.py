"""Local screenshot shortlist. Rebuild with python -m backend.analytics.shortlist."""
from dataclasses import dataclass
from pathlib import Path
import csv
import hashlib
import json
import re

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from .context import RAW, ROOT, classify, load_context


VERSION = "shortlist-1.1"
CUTOFF = "2026-11-01"
SEED = 20271117
DRAWS = 800
EXCLUDED_SELECTION_IDS = {8}  # User exclusion, applied only to selection.
KINDS = ("bat", "bowl")
PID = {"bat": "striker_id", "bowl": "bowler_id"}
TIER_LABELS = ("Unrated", "Provisional", "Supporting", "Substantial")
GATES = {"bat": {3: (300, 80, 15, 8), 2: (100, 25, 5, 4)},
         "bowl": {3: (360, 100, 15, 10), 2: (72, 18, 4, 4)}}
PHASES = ("Powerplay", "Middle", "Death")


@dataclass(frozen=True)
class Candidate:
    name: str
    bat_id: int
    affiliation: str
    bowl_id: int | None = None
    bowl_affiliation: str | None = None

    def player_id(self, kind):
        return (self.bowl_id or self.bat_id) if kind == "bowl" else self.bat_id

    def team_label(self, kind):
        return (self.bowl_affiliation or self.affiliation) if kind == "bowl" else self.affiliation


# Exact screenshot strings, with IDs adjudicated by team and discipline before scoring.
POOL = (
    Candidate("Rohit Sharma", 126, "India / Mumbai Indians"),
    Candidate("Shikhar Dhawan", 142, "Punjab Kings"),
    Candidate("Dinesh Karthik", 143, "India / Royal Challengers Bengaluru"),
    Candidate("Pradeep Sangwan", 147, "Gujarat Titans"),
    Candidate("Ravindra Jadeja", 152, "India / Rajasthan Royals / Chennai Super Kings"),
    Candidate("Amit Mishra", 158, "Lucknow Super Giants"),
    Candidate("Dwayne Bravo", 161, "Chennai Super Kings"),
    Candidate("Piyush Chawla", 23, "Mumbai Indians"),
    Candidate("Ishant Sharma", 28, "Delhi Capitals / Gujarat Titans"),
    Candidate("Nathan Bracken", 35, "Roster entry only"),
    Candidate("Virat Kohli", 47, "India / Royal Challengers Bengaluru"),
    Candidate("Faf du Plessis", 88, "Royal Challengers Bengaluru / Delhi Capitals"),
    Candidate("Wriddhiman Saha", 109, "Gujarat Titans"),
    Candidate("Rashid Khan", 4722, "Afghanistan / Gujarat Titans"),
    Candidate("Abdul Samad", 7446, "Sunrisers Hyderabad / Lucknow Super Giants"),
    Candidate("Haider Ali", 7338, "Pakistan / Pakistan A", 28756, "United Arab Emirates"),
    Candidate("Basil Hameed", 8638, "United Arab Emirates"),
    Candidate("Muhammad Farooq", 27373, "United Arab Emirates"),
    Candidate("Bashir Ahmad", 29833, "Afghanistan"),
    Candidate("Mahendra Singh Dhoni", 8, "Chennai Super Kings"),
)


def verify_sources(raw, roster, base, inventory):
    """Check joins and raw fingerprint without treating coverage gaps as fake zeroes."""
    tables = {
        "competitions.csv": ("comp_id",),
        "teams.csv": ("comp_id", "team_id"),
        "matches.csv": ("match_id",),
        "playing_eleven.csv": ("match_id", "team_id", "player_id"),
        "competition_team_player_mapping.csv": ("comp_id", "team_id", "player_id"),
    }
    source = {name: pd.read_csv(raw / name) if name != "competition_team_player_mapping.csv" else roster
              for name in tables}
    joins = {}
    for name, key in tables.items():
        rows = source[name]
        repeated = int(rows.duplicated(list(key)).sum())
        if repeated and name in {"matches.csv", "competitions.csv"}:
            raise ValueError(f"Duplicate key {key} in {name}")
        # XI and team/roster tables are used as membership sets, never as row-multiplying joins.
        joins[name] = {"rows": len(rows), "key": list(key), "columns": len(rows.columns), "repeated_keys": repeated}
    joins["ball_by_ball.csv"] = {
        "rows": len(base), "key": ["match_id", "innings", "innings_ball_num"],
        "columns": len(pd.read_csv(raw / "ball_by_ball.csv", nrows=0).columns),
    }
    file_hashes = {Path(x["file"].replace("\\", "/")).name: x["sha256"] for x in inventory["files"]}
    for path in sorted(raw.glob("*")):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != file_hashes.get(path.name):
            raise ValueError(f"Supplied file changed since inventory: {path.name}")
        if path.name in joins:
            joins[path.name]["sha256"] = digest
    if set(tables) | {"ball_by_ball.csv"} != set(joins):
        raise ValueError("Expected six CSVs")
    team_keys = pd.MultiIndex.from_frame(source["teams.csv"][["comp_id", "team_id"]])
    xi_keys = pd.MultiIndex.from_frame(source["playing_eleven.csv"][["match_id", "team_id", "player_id"]])
    roster_keys = pd.MultiIndex.from_frame(roster[["comp_id", "team_id", "player_id"]])
    coverage = {"deliveries_missing_match_or_competition": int(base.match_date.isna().sum()
                + (base.match_date.notna() & base.comp_name.isna()).sum())}
    if coverage["deliveries_missing_match_or_competition"]:
        raise ValueError("Unresolved delivery to match/competition join")
    for side, pid, team in [("striker", "striker_id", "batting_team_id"),
                            ("bowler", "bowler_id", "bowling_team_id")]:
        coverage[f"{side}_team_not_in_competition"] = int(
            (~pd.MultiIndex.from_frame(base[["comp_id", team]]).isin(team_keys)).sum())
        coverage[f"{side}_not_in_xi"] = int(
            (~pd.MultiIndex.from_frame(base[["match_id", team, pid]]).isin(xi_keys)).sum())
        coverage[f"{side}_not_in_roster"] = int(
            (~pd.MultiIndex.from_frame(base[["comp_id", team, pid]]).isin(roster_keys)).sum())
    return joins, coverage


def audited_deliveries(base):
    """Keep a separate alternative for the unresolved end/length review."""
    dls = base.result.fillna("").str.contains(r"\bD\s*/\s*L\b|\bDLS\b|Duckworth", case=False, regex=True)
    model = base[base.eligible_context & base.match_format.isin(("T20", "T20I")) & ~dls]
    inn = model.groupby(["match_id", "innings"]).agg(
        last_over=("overid", "max"), wickets=("is_wicket", "sum"),
        batting=("batting_team_id", "first"), winner=("win_team_id", "first"),
        legal=("legal", "sum"),
    ).reset_index()
    suspect = inn[(inn.last_over < 20) & (inn.wickets < 10)
                  & ((inn.innings == 1) | (inn.batting != inn.winner))]
    flagged_matches = sorted(map(int, suspect.match_id.unique()))
    wide_scope = model[model.legal].copy()
    primary = wide_scope[~wide_scope.match_id.isin(flagged_matches)].copy()
    flags = {
        "dls_text_match_ids": sorted(map(int, base.loc[dls, "match_id"].unique())),
        "previously_accepted_dls_match_ids": sorted(map(int, base.loc[dls & base.eligible_context, "match_id"].unique())),
        "unresolved_endings": suspect.drop(columns=["winner"]).to_dict("records"),
        "unresolved_match_ids": flagged_matches,
        "additional_dls_legal_balls_quarantined": int((base.eligible_context & base.legal & dls).sum()),
        "additional_ambiguous_legal_balls_quarantined": len(wide_scope) - len(primary),
    }
    return primary, wide_scope, flags


class PeerExpectations:
    """Hierarchical run and dismissal rates, with a leave-player-out peer set."""

    def __init__(self, train, kind):
        self.pid = PID[kind]
        self.out = kind + "_out"
        self.role = "bat_role" if kind == "bat" else "style"
        self.groups = [
            [],
            ["phase", "innings", self.role],
            ["family", "phase", "innings", self.role],
            ["year", "family", "phase", "innings", self.role],
        ]
        self.measures = ["peer_n", "peer_runs", "peer_outs"]
        self.total = np.array([len(train), train.runs.sum(), train[self.out].sum()], dtype=float)
        self.tables = []
        for keys in self.groups:
            broad = self.aggregate(train, keys) if keys else None
            own = self.aggregate(train, [*keys, self.pid])
            self.tables.append((broad, own))

    def aggregate(self, train, keys):
        return train.groupby(keys, observed=True).agg(peer_n=("runs", "size"),
                                                     peer_runs=("runs", "sum"),
                                                     peer_outs=(self.out, "sum"))

    def expected(self, rows):
        n = len(rows)
        # Start with an observed global peer distribution, then refine by cricket role and context.
        rate = np.zeros((n, 2), dtype=float)
        needed = list(dict.fromkeys([self.pid, *self.groups[-1]]))
        query = rows[needed]
        for keys, (broad, own), prior in zip(self.groups, self.tables, [0, 120, 240, 240]):
            rest = ((query.join(broad, on=keys)[self.measures].fillna(0).to_numpy(dtype=float))
                    if keys else self.total)
            rest = rest - query.join(own, on=[*keys, self.pid])[self.measures].fillna(0).to_numpy(dtype=float)
            denominator = rest[:, :1] + prior
            rate = np.divide(rest[:, 1:] + prior * rate, denominator, out=rate.copy(), where=denominator > 0)
        return rate

    def residuals(self, rows, kind):
        expectation = self.expected(rows)
        sign = 1 if kind == "bat" else -1
        return (sign * (rows.runs.to_numpy() - expectation[:, 0]),
                -sign * (rows[self.out].to_numpy() - expectation[:, 1]))


def with_context(frame, fit=None):
    frame = frame.copy()
    reference = frame if fit is None else fit
    for kind in KINDS:
        frame[kind + "_run_value"], frame[kind + "_wicket_value"] = PeerExpectations(reference, kind).residuals(frame, kind)
    return frame


def innings_stats(frame, kind, wicket=12):
    pid = PID[kind]
    q = frame[kind + "_run_value"] + wicket * frame[kind + "_wicket_value"]
    high = frame[kind + "_pressure"].eq("High")
    side = pd.DataFrame({
        "player_id": frame[pid], "match_id": frame.match_id, "innings": frame.innings,
        "balls": 1, "runs": frame.runs, "outs": frame[kind + "_out"],
        "quality": q, "high_balls": high.astype(int), "high_quality": q.where(high, 0),
        "high_runs": frame.runs.where(high, 0), "high_outs": frame[kind + "_out"].where(high, 0),
    })
    return side.groupby(["player_id", "match_id", "innings"], sort=True).sum().reset_index()


STATS = ["balls", "high_balls", "quality", "high_quality"]


def measures(totals):
    balls, high, quality, high_q = np.moveaxis(np.asarray(totals, dtype=float), -1, 0)
    usual = (quality - high_q) / (balls - high + 120)
    pressured = (high_q + 60 * usual) / (high + 60)
    lift = pressured - usual
    return usual * 6, pressured * 6, lift * 6, 6 * (.75 * pressured + .25 * lift)


def estimates(matched, kind, player_id, draws=DRAWS):
    totals = matched[STATS].sum().to_numpy()
    balls, high, _, _ = totals
    if high == 0 or high == balls:
        return None
    usual, pressed, lift, point = map(float, measures(totals))
    result = {"usual": usual, "pressure": pressed, "lift": lift, "point": point,
              "score": None, "low": None, "high": None}
    if matched.high_balls.gt(0).sum() >= 4:
        rng = np.random.default_rng(SEED + int(player_id)*2 + int(kind == "bowl"))
        n = len(matched)
        weights = rng.multinomial(n, np.full(n, 1 / n), size=draws)
        # Hold peer expectations fixed; a pressure-free resample uses the stated shrinkage rule.
        values = measures(weights @ matched[STATS].to_numpy())[-1]
        low, score, high = map(float, np.quantile(values, [.025, .2, .975]))
        result.update(score=score, low=low, high=high)
    return result


def evidence_tier(kind, role_ok, totals, n_innings, n_high_innings, n_high_matches):
    balls, high = int(totals["balls"]), int(totals["high_balls"])
    if not role_ok:
        return 0, "Role screen not met" if balls else "No validated deliveries in this discipline"
    if not high:
        return 0, "No high-pressure legal balls"
    if high == balls:
        return 0, "No non-high comparator"
    counts = (balls, high, n_innings, n_high_innings)
    for tier, gate in GATES[kind].items():
        if n_high_matches >= 4 and all(value >= threshold for value, threshold in zip(counts, gate)):
            return tier, "Meets the " + TIER_LABELS[tier].lower() + " sample gate"
    return 1, "Below the supporting sample gate"


def measured_role(kind, side, per_innings):
    if side.empty:
        return False, "No observed role", None
    if kind == "bowl":
        return bool(per_innings.balls.max() >= 12), str(side.bowling_type.mode().iloc[0]), None
    pos = float(side.groupby(["match_id", "innings"]).batting_order.first().median())
    return (bool(len(per_innings) >= 5 and 1 <= pos <= 8),
            "Top-order batter" if pos <= 3 else "Middle-order batter" if pos <= 5 else
            "Finisher / lower order" if pos <= 8 else "Tail order", pos)


def order_key(player):
    tier = player["tier_code"]
    e = player["estimates"]
    high = player["sample"]["high_balls"]
    matches = player["sample"]["high_matches"]
    identity = (player["name"].casefold(), player["id"])
    if tier >= 2:
        return (-2, -e["score"], -high, -matches, *identity)
    if tier == 1:
        return (-tier, -matches, -high, -e["point"], *identity)
    return (0, *identity)


def slices(frame, kind):
    """Observed stats and an adjusted quality rate, always scoped to the displayed balls."""
    value = frame[kind + "_run_value"] + 12 * frame[kind + "_wicket_value"]
    result = {"balls": len(frame), "runs": int(frame.runs.sum()), "outs": int(frame[kind + "_out"].sum())}
    result["rate"] = round(result["runs"] * (100 if kind == "bat" else 6) / len(frame), 2) if len(frame) else None
    result["adjusted_impact"] = round(float(value.mean()) * 6, 3) if len(frame) else None
    return result


def scouting_note(kind, role, phase):
    if kind == "bat":
        return {"Top-order batter": "Screen for opening depth and powerplay scoring.",
                "Middle-order batter": "Screen for innings repair in the middle overs.",
                "Finisher / lower order": "Screen for finishing and batting depth."}.get(role, "No reliable batting role from this sample.")
    if role == "No observed role":
        return "No reliable bowling role from this sample."
    text = {"Powerplay": "Screen for new-ball overs.",
            "Middle": "Screen for middle-over matchups.",
            "Death": "Screen for late-over coverage."}.get(phase, "Screen for bowling depth.")
    return f"{text} Observed style: {role}."


def identity_audit(roster, raw_rows):
    result = {}
    if len({p.name for p in POOL}) != 20:
        raise ValueError("Expected 20 unique exact dropdown strings")
    for p in POOL:
        named = roster[roster.player_name.eq(p.name)]
        ids = set(map(int, named.player_id.unique()))
        if not {p.player_id(k) for k in KINDS} <= ids:
            raise ValueError(f"Explicit source identity missing for {p.name}")
        result[p.name] = [{
            "id": int(pid), "teams": sorted(rows.team_name.unique()),
            "used_for": [k for k in KINDS if p.player_id(k) == pid],
            "raw_batting_events": int(raw_rows.striker_id.eq(pid).sum()),
            "raw_bowling_events": int(raw_rows.bowler_id.eq(pid).sum()),
        } for pid, rows in named.groupby("player_id", sort=True)]
    return result


def candidate_results(frame, kind, identity, wicket=12, details=False):
    side = frame[frame[PID[kind]].isin([p.player_id(kind) for p in POOL])]
    inning_groups = {int(pid): g for pid, g in innings_stats(side, kind, wicket).groupby("player_id")}
    ball_groups = {int(pid): g for pid, g in side.groupby(PID[kind])}
    zero_stats = side.iloc[:0]
    zero_innings = innings_stats(zero_stats, kind, wicket)
    result = []
    for candidate in POOL:
        pid = candidate.player_id(kind)
        if pid in EXCLUDED_SELECTION_IDS:
            continue
        g = inning_groups.get(pid, zero_innings)
        b = ball_groups.get(pid, zero_stats)
        total = g.sum(numeric_only=True)
        matches = g.groupby("match_id")[STATS].sum()
        n_high_m = int(matches.high_balls.gt(0).sum())
        n_high_i = int(g.high_balls.gt(0).sum())
        role_ok, role, position = measured_role(kind, b, g)
        tier, reason = evidence_tier(kind, role_ok, total, len(g), n_high_i, n_high_m)
        batting_or_bowling = {
            "name": candidate.name, "id": pid, "affiliation": candidate.team_label(kind),
            "identity_ambiguous": len(identity[candidate.name]) > 1, "role": role,
            "tier": TIER_LABELS[tier], "tier_code": tier, "reason": reason,
            "rank": None, "estimates": estimates(matches, kind, pid) if tier else None,
            "sample": {
                "balls": int(total.balls), "high_balls": int(total.high_balls),
                "innings": len(g), "high_innings": n_high_i, "matches": len(matches),
                "high_matches": n_high_m,
                "last_seen": max(b.match_date) if len(b) else None,
            },
        }
        if details:
            high_mask = b[kind + "_pressure"].eq("High")
            high = b[high_mask]
            non_high = b[~high_mask]
            phases = [{ "phase": phase, **slices(b[b.phase.eq(phase)], kind),
                        "high_balls": int((high.phase == phase).sum())} for phase in PHASES]
            most_phase = max(phases, key=lambda p: p["balls"])["phase"] if len(b) else None
            examples = []
            for (match_id, inns), observations in high.groupby(["match_id", "innings"], sort=True):
                examples.append({
                    "match_id": int(match_id), "innings": int(inns), "date": observations.match_date.iloc[0],
                    "competition": observations.comp_name.iloc[0],
                    "pressure_reasons": observations[kind + "_reason"].value_counts().index.tolist(),
                    "source_rows": observations.source_row.head(4).astype(int).tolist(),
                    **slices(observations, kind)
                })
            examples.sort(key=lambda e: (-e["balls"], e["date"], e["match_id"]))
            batting_or_bowling.update(
                position=position, high=slices(high, kind), non_high=slices(non_high, kind), phases=phases,
                examples=examples[:3], competitions=sorted(b.family.unique()),
                rr_note=scouting_note(kind, role, most_phase),
            )
        result.append(batting_or_bowling)
    result.sort(key=order_key)
    ranked = [r for r in result if r["tier_code"] > 0][:10]
    for index, row in enumerate(ranked, start=1):
        row["rank"] = index
    return {"ranking": ranked, "candidates": result}


def bounded_rank_check(ranking):
    allow = {candidate.name for candidate in POOL}
    for kind, side in ranking.items():
        names = [r["name"] for r in side["ranking"]]
        assert set(names) <= allow
        assert len(names) == len(set(names))
        assert [r["rank"] for r in side["ranking"]] == list(range(1, len(names)+1))
        assert len(side["candidates"]) == len(allow) - 1
        assert all(r["tier_code"] and r["sample"]["high_balls"] for r in side["ranking"])
        resolved = {p.name: p.player_id(kind) for p in POOL}
        assert all(resolved[r["name"]] == r["id"] for r in side["ranking"])


def score_sensitivity(primary, wide, ranking, identities):
    """Recompute all metrics within each scenario; membership includes only scored names."""
    # Labels depend on pre-delivery columns; existing context residuals stay fixed for rule shifts.
    # For IPL-only or changed data coverage, refit the peer baseline within that scope.
    scenarios = [
        ("Looser pressure", classify(primary, shift=-1), 12),
        ("Stricter pressure", classify(primary, shift=1), 12),
        ("Wicket value 8", primary, 8),
        ("Wicket value 16", primary, 16),
        ("IPL only", with_context(primary[primary.family.eq("IPL")]), 12),
        ("Allow unresolved endings", with_context(classify(wide)), 12),
    ]
    records = {}
    for kind in KINDS:
        default = {r["name"]: r for r in ranking[kind]["ranking"]}
        results = []
        for label, frame, wicket in scenarios:
            side = candidate_results(frame, kind, identities, wicket)["ranking"]
            changed = {r["name"]: r["rank"] for r in side}
            shifts = [{"player": name, "base": row["rank"], "scenario": changed.get(name)}
                      for name, row in default.items() if changed.get(name) != row["rank"]]
            results.append({"scenario": label, "ranked": len(side), "overlap": len(set(default) & set(changed)),
                            "order": list(changed), "shifts": shifts})
        records[kind] = results
    return records


def rho(xs, ys):
    if len(xs) < 5 or len(set(xs)) < 2 or len(set(ys)) < 2:
        return None
    return round(float(spearmanr(xs, ys).statistic), 3)


def chronological(primary):
    rows = {k: [] for k in KINDS}
    allow_ids = {k: {p.player_id(k) for p in POOL} for k in KINDS}
    for year in (2024, 2025, 2026):
        train = primary[primary.year.lt(year)]
        future = primary[primary.year.eq(year)]
        assert not set(train.match_id).intersection(future.match_id)
        for kind in KINDS:
            model = PeerExpectations(train, kind)
            def transform(segment):
                segment = segment.copy()
                segment[kind + "_run_value"], segment[kind + "_wicket_value"] = model.residuals(segment, kind)
                return innings_stats(segment, kind)
            a, b = transform(train), transform(future)
            eval_groups = {pid: g for pid, g in b.groupby("player_id")
                           if g.high_balls.sum() >= 24 and g.loc[g.high_balls.gt(0), "match_id"].nunique() >= 3}
            train_sides = {pid: g for pid, g in train[train[PID[kind]].isin(eval_groups)].groupby(PID[kind])}
            forecast_rows = []
            for pid, matches in a[a.player_id.isin(eval_groups)].groupby("player_id"):
                totals = matches.sum(numeric_only=True)
                training_matches = matches.groupby("match_id")[STATS].sum()
                role_ok, _, _ = measured_role(kind, train_sides[pid], matches)
                tier, _ = evidence_tier(kind, role_ok, totals, len(matches), matches.high_balls.gt(0).sum(),
                                        training_matches.high_balls.gt(0).sum())
                if tier < 2:
                    continue
                heldout = eval_groups[pid]
                previous = estimates(training_matches, kind, pid)
                forecast_rows.append({
                    "pid": int(pid), "tier": tier, "proposed": previous["score"],
                    "pressure_only": totals.high_quality * 6 / (totals.high_balls + 60),
                    "usual": previous["usual"], "observed": heldout.high_quality.sum() * 6 / heldout.high_balls.sum(),
                })
            for scope, samples in [("All covered players", forecast_rows),
                                   ("Screenshot candidates", [x for x in forecast_rows if x["pid"] in allow_ids[kind]])]:
                # Replay tier priority before score, with ties in the diagnostic left tied.
                ordering = sorted(set((min(r["tier"], 2), r["proposed"]) for r in samples))
                ranks = {item: i for i, item in enumerate(ordering)}
                actual = [r["observed"] for r in samples]
                rows[kind].append({
                    "scope": scope, "test_year": year, "train_through": year - 1, "common_players": len(samples),
                    "proposed": rho([ranks[(min(r["tier"], 2), r["proposed"])] for r in samples], actual),
                    "pressure_only": rho([r["pressure_only"] for r in samples], actual),
                    "usual": rho([r["usual"] for r in samples], actual),
                })
    return rows


def publish_local(snapshot, out):
    """Write the canonical results and the local browser/export copies."""
    out.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, allow_nan=False)
    snapshot["build_id"] = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
    data = json.dumps(snapshot, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    public = ROOT / "frontend" / "public"
    cols = ["category", "rank", "form_name", "source_id", "source_identity", "tier", "legal_balls", "high_balls",
            "high_innings", "high_matches", "last_seen", "conditional_score", "point_estimate",
            "conditional_95_low", "conditional_95_high", "verify_dropdown_identity", "snapshot"]
    selection = out / "Shortlist_Form_Selections.csv"
    def replace(path, content):
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_bytes(content)
        tmp.replace(path)
    with selection.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=cols)
        writer.writeheader()
        for kind, side in snapshot["categories"].items():
            for row in side["ranking"]:
                e, sample = row["estimates"], row["sample"]
                writer.writerow({
                    "category": "Batsman" if kind == "bat" else "Bowler", "rank": row["rank"], "form_name": row["name"],
                    "source_id": row["id"], "source_identity": row["affiliation"], "tier": row["tier"],
                    "legal_balls": sample["balls"], "high_balls": sample["high_balls"],
                    "high_innings": sample["high_innings"], "high_matches": sample["high_matches"],
                    "last_seen": sample["last_seen"], "conditional_score": e["score"], "point_estimate": e["point"],
                    "conditional_95_low": e["low"], "conditional_95_high": e["high"],
                    "verify_dropdown_identity": "Yes" if row["identity_ambiguous"] else "",
                    "snapshot": snapshot["build_id"],
                })
    replace(out / "shortlist.json", data.encode("utf-8"))
    replace(public / "shortlist.json", data.encode("utf-8"))
    replace(public / selection.name, selection.read_bytes())


def build(raw=RAW, out=ROOT / "output" / "shortlist"):
    base, initial = load_context(raw, cutoff=CUTOFF)
    roster = pd.read_csv(raw / "competition_team_player_mapping.csv")
    inventory = json.loads((ROOT / "output" / "dataset_inventory.json").read_text(encoding="utf-8"))
    sources, joins = verify_sources(raw, roster, base, inventory)
    identities = identity_audit(roster, base)
    audited, wide, flags = audited_deliveries(base)
    primary = with_context(classify(audited))
    assert primary.source_row.is_unique
    assert len(primary) + flags["additional_ambiguous_legal_balls_quarantined"] \
        + flags["additional_dls_legal_balls_quarantined"] == initial["legal_model_deliveries"]
    ranking = {kind: candidate_results(primary, kind, identities, details=True) for kind in KINDS}
    bounded_rank_check(ranking)
    v1 = json.loads((ROOT / "output" / "model_v2_audit.json").read_text(encoding="utf-8"))
    snapshot = {
        "version": VERSION, "source_cutoff": CUTOFF,
        "source_start": initial["source_date_min"], "identities": identities, "categories": ranking,
        "method": {
            "point": "6 × (0.75 × adjusted pressure impact per ball + 0.25 × lift versus usual per ball)",
            "unit": "Adjusted run equivalents per six legal balls",
            "gates": {k: {TIER_LABELS[t]: list(g) for t, g in values.items()} for k, values in GATES.items()},
            "bootstrap_draws": DRAWS, "wicket_value": 12, "bootstrap_quantile": 0.2,
            "holdout_min_high_balls": 24, "holdout_min_high_matches": 3,
        },
        "audit": {
            "source_files": sources, "join_coverage": joins, "v1_deliveries": initial,
            "accepted_legal_balls": len(primary), "accepted_matches": int(primary.match_id.nunique()),
            "accepted_innings": int(primary.groupby(["match_id", "innings"]).ngroups),
            "families": {str(f): int(n) for f, n in primary.family.value_counts().items()},
            "excluded_extra_review": flags, "source_unchanged": True,
        },
        "validation": {
            "sensitivity": score_sensitivity(primary, wide, ranking, identities),
            "chronological": chronological(primary),
            "legacy_holdout": {kind: v1["categories"][kind]["holdout"] for kind in KINDS},
        },
    }
    publish_local(snapshot, out)
    return snapshot


if __name__ == "__main__":
    data = build()
    print(f"Shortlist {data['build_id']}: {data['audit']['accepted_legal_balls']:,} legal balls")
    for kind, values in data["categories"].items():
        for row in values["ranking"]:
            print(kind, row["rank"], row["name"], row["tier"], f"{row['sample']['high_balls']} high")
