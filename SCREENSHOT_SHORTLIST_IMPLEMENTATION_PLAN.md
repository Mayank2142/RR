# SupeRR Selector: screenshot shortlist implementation plan

**Prepared 17 November 2026 · Local only · Historical analysis through 1 November 2026**

## 1. Deliverables and rules

1. Two ordered lists: ten batter names and ten bowler names, with exactly the spelling shown in the screenshots. Only the 20 distinct visible names may enter either table. The same person can qualify in both disciplines; no display name repeats within a list. The screenshots show a batter dropdown, so they establish the name pool, not live bowler-dropdown or auction eligibility.
2. A local React dashboard with both lists, identity and sample information, profile drill-down, comparable evidence, model diagnostics, and a PDF download.
3. A methodology report in PDF, plus a local CSV with rank, exact form name, identity, and evidence status. The report and dashboard will read the same computed snapshot. No upload, public link, or form submission.

The existing whole-pack rankings and PDF are a baseline. The new restricted package gets separate files and a clearly identified dashboard view. The official brief calls for pressure performance compared with each player's usual level. Rankings should describe the sample; player availability, retention, injuries, IPL eligibility, and the 2027 auction pool are outside the supplied evidence.

## 2. Audit all six inputs and resolve identities

| Input | Rows in supplied pack | Check and use |
|---|---:|---|
| `ball_by_ball.csv` | 200,999 | Unique match, innings and event sequence; ID, event order, legal delivery and outcome checks. |
| `matches.csv` | 883 | Unique match ID, date, result, revisions and pre-match knockout indicator. Sixteen match IDs have no delivery rows. |
| `competitions.csv` | 141 | Verify format, family and season for peer adjustments and IPL sensitivity. |
| `competition_team_player_mapping.csv` | 6,413 | Resolve each screenshot spelling to ID candidates and competition-team context. |
| `playing_eleven.csv` | 28,381 | Cross-check player, team, match and role, without counting roster appearances as batting or bowling evidence. |
| `teams.csv` | 353 | Verify teams within each competition; keep ID/name conflicts visible. |

Use the complete legal-ball data as the **peer reference**, and the screenshot whitelist as the **only output pool**. Reconcile raw and accepted rows and preserve a pointer to original delivery rows. Record source hashes for reproducibility.

- Deduplicate Rohit Sharma across screenshots. Keep distinct IDs separate for Rashid Khan, Abdul Samad and Haider Ali. Use Afghanistan's Rashid Khan (4722) and the IPL Abdul Samad (7446) as the declared matches for this IPL shortlist. Pakistan's Haider Ali (7338) is the batting candidate; UAE's Haider Ali (28756) is the bowling candidate. Print the respective team and ID wherever either appears. Verify the dropdown identity before form entry if the site exposes only the bare name.
- Keep unverified same-name records separate for Basil Hameed, Muhammad Farooq, and Bashir Ahmad. For each display name use the ID with the relevant documented senior delivery sample, preserve the alternate IDs in the audit, and do not pool their balls. Nathan Bracken is in the roster mapping but has no delivery sample.
- Use confirmed legal deliveries in regular T20 innings. Exclude unknown extras events affecting the legal sequence, malformed sequences, super overs and abandoned/revised games. Review D/L or DLS result text even where numeric revision fields are empty. Quarantine ambiguous early endings without inventing an allocation. Test again with the ambiguous cases reinstated as a data-quality sensitivity check.
- The primary extras column is a category code, and the secondary field cannot reconstruct all team scores. Use recorded off-bat runs, striker dismissals, and credited bowler wickets. Exclude run-outs from bowler credit. Label the resulting rates as runs per 100 legal balls (batting) and off-bat runs per six legal balls (bowling). Required run rate, official economy, exact chase pressure and win probability are unavailable from this pack.

## 3. Define pressure before looking at an outcome

Keep the documented v1 default pressure triggers so the labels can be checked against the earlier work. Batting pressure is depleted resources: early or middle-over collapse, a late chase short on wickets, or a knockout with depleted wickets. Bowling pressure is established opposition: a set striker or partnership, especially in the death overs or knockouts. A death over by itself does not make a delivery high pressure. Use only state known before the ball; high versus non-high is the primary comparison. Retain looser and stricter definitions as sensitivity scenarios.

## 4. Rank repeatable performance and show evidence strength

1. Estimate peer scoring and dismissal/wicket expectations for the same innings, phase, role, competition family and match year. Exclude the player's own observations in each descriptive peer estimate. Shrink sparse cells toward broader matching peers. For a chronological test, fit on past matches only and use a season-independent fallback for a held-out year.
2. Each legal ball gets a signed context residual. Batting adds scoring above peer expectation and subtracts 12 times excess striker dismissals. Bowling adds off-bat run suppression and 12 times excess credited wickets. The wicket value is an assumption; rerun at 8 and 16. Higher is better in both disciplines, in run equivalents.
3. Calculate usual performance `U = non-high residual sum / (non-high balls + 120)`. Estimate pressure performance `P = (high residual sum + 60 × U) / (high balls + 60)`. Estimate pressure lift `L = P − U`. The point measure is `6 × (0.75 × P + 0.25 × L)`, in adjusted run equivalents per six legal balls. Shrinkage reduces the influence of tiny samples. No pressure score is assigned when there are no high balls or no non-high comparator.
4. Resample whole matches for each player, with a fixed seed. Across all supported candidates use the 20th percentile of the resampled point measure as the ordering score; show the point estimate and conditional 95% interval. The interval assumes the data and pressure rules are fixed. It does not measure 2027 performance or joint rank probabilities. With fewer than four matches containing pressure balls, show counts and no interval.
5. Admit batter roles with at least five observed batting innings and a typical position of 1–8; admit bowling roles with at least one observed spell of 12 legal balls. These screens prevent incidental use from passing for the primary skill. Apply the following evidence tiers before ordering:

   | Tier | Batter: legal balls / high balls / innings / high innings | Bowler: legal balls / high balls / innings / high innings |
   |---|---|---|
   | Substantial | 300 / 80 / 15 / 8 | 360 / 100 / 15 / 10 |
   | Supporting | 100 / 25 / 5 / 4 | 72 / 18 / 4 / 4 |
   | Provisional | A plausible batting role with both pressure and non-pressure evidence below those gates | A plausible bowling role with both pressure and non-pressure evidence below those gates |
   | Unrated | No pressure observations, no comparator, or role screen not met | No pressure observations, no comparator, or role screen not met |

   Version 1.1 pools substantial and supporting candidates and orders them by the conservative score; evidence tier remains visible as a sample descriptor. Threshold checks for these tiers also require at least four distinct pressure matches. If necessary, fill remaining places with explicitly provisional names ordered by distinct pressure matches, then pressure balls, then the point estimate. Leave a slot unfilled if even provisional evidence runs out; reputation alone cannot fill it. Break exact ties by higher pressure sample and stable name/ID order. Show last qualifying date separately so historical performance is not confused with current activity.

## 5. Check whether the order holds up

- Recompute with the looser/stricter rules, wicket values 8 and 16, and IPL-only evidence; show top-ten overlap, how many slots can be supported, and which marginal names move. Check the ambiguous-innings policy separately.
- Run whole-match chronological folds using earlier seasons for fitting and ranking, then measure next-season adjusted pressure performance for common players with meaningful holdout samples. Compare the proposed score with a shrunken pressure-only estimate, usual performance, and the original v1 fold results with sample context. Report counts and Spearman correlation for each usable fold and the restricted cohort when large enough. Previously examined years are retrospective checks.
- Do not claim a stronger forecast unless results support it. A historical shortlist can still be useful when future performance is uncertain. Report unstable or close ranks and weak evidence directly.
- Verify logical delivery keys, counts, ID collisions, leave-player-out peer calculations, bowling-credit and current-ball leakage checks, cold/no-evidence cases, deterministic rebuilds, and exact matching JSON/CSV/PDF names and order.

## 6. Build and verify the local package

| Sequence | Build | Done when |
|---|---|---|
| 1 | Candidate whitelist, audit and cleaned context | Every displayed name maps to an explicit source identity or an unrated reason; source files are unchanged. |
| 2 | Restricted ratings, sensitivity and backtesting | A single JSON snapshot contains the ordered tables, sample tiers, estimates, uncertainty, context, source-row examples and audit notes. Export exact form names and evidence in CSV. |
| 3 | Dashboard | The landing view shows the restricted lists and report button. Each row opens a profile with high vs non-high statistics, phases, and match/row evidence. A comparison view explains uncertainty. An audit view shows rejected candidates, identity caveats and what the source can measure. Phone and desktop layouts work. |
| 4 | Report | A readable PDF covers the official brief: two tables, data and pressure definition, ratings and calculations, match evidence, reliability checks and limits. Each selected player has a conditional RR screening note tied to role and sample. |
| 5 | Final review | Reopen the PDF, audit the exported names and tiers against the dashboard, verify downloads and interactions locally, and provide the exact ten-by-ten table and local files in the handoff. |

The deeper research work in `ALGORITHM_V2_PLAN.md` is a separate track. Exact chase and win models require verified scoreboard data that are absent from this pack. The restricted package can be reproduced using the supplied files alone.
