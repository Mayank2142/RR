# SupeRR Selector algorithm v2: implementation plan

Prepared 11 November 2026. This is a proposed replacement methodology, supported by an audit of the current implementation. V2 has not been trained or shown to outperform v1. Keep all work local, following the user's delivery preference.

The objective is to select players with strong, repeatable performance in comparable pressure situations. Increasing a score, adding a more complex model, or producing more familiar names does not establish that selection improved.

## 1. What the current evidence says

The following measurements come from `output/analysis.json`, with reproducible review findings in `output/model_v2_audit.json`.

| Finding | Observed result | Implication for v2 |
|---|---|---|
| Batting chronological holdout | Spearman -0.1695, 35 common players | The existing batting score does not demonstrate useful positive association with later pressure impact in this diagnostic. Treat the current ordering as provisional. |
| Bowling chronological holdout | Spearman +0.3399, 31 common players | Exploratory evidence, with a small evaluated cohort. Compare against simpler baselines before claiming selection value. |
| Batting pressure-rule sensitivity | Only 5 of 10 players retained under both the looser and stricter alternatives | Pressure definition is a larger unresolved issue than choosing slightly different component weights. |
| Competition dependence | IPL-only overlap: batting 8/10, bowling 6/10 | International performance cannot be assumed to transfer unchanged into the IPL. |
| Top-ranked bowler's evidence | Rasikh Salam: 138 high-pressure legal balls; conditional score interval 56.41-93.77 | A stable rank under weight changes is not proof that this player is truly the best or more reliable than another player. |
| Batting role distribution | Top 10: 4 lower-order, 5 middle-order, 1 top-order; eligible cohort: 23, 49, 27 respectively | Investigate role exposure and comparability. This distribution alone is not proof of bias and does not justify imposing quotas. |
| Innings ending/allocation review | 11 retained innings end before over 20 without 10 recorded wickets and are not straightforward successful chases | Some may be legitimate shortened or retired-hurt endings. The audit flag requires adjudication, not automatic exclusion. |
| Missing extras | `extras1_runs` behaves as a category code, not a run amount | Full scoreboard pressure and complete bowling economy require verified additional evidence. |

Two specific review examples are match 20182, whose result text says D/L despite null numeric revision fields, and match 31278, where both retained innings have 96 legal balls. The latter is a possible shortened-allocation case that must be verified. Never infer a match's scheduled length from an early successful chase.

## 2. Define two outputs before optimizing anything

**Round 1 pressure reliability:** assess the supplied historical performance using comparable contexts and honest uncertainty. This is the submission ranking.

**RR scouting priority:** estimate suitability for a specified IPL role as of a stated date, then apply verified registration, availability and squad constraints. This is a separate decision view. Availability must not silently alter the historical contest ranking.

Create an experiment specification before tuning:

- Data cutoff, source hashes, target competition and model version.
- Batting and bowling targets, pressure situations, opportunity rules and intended role.
- Validation folds, baseline algorithms and primary evaluation metrics.
- Which assumptions are domain policy and which are estimated from data.
- A rule for adopting v2 only after an actual comparison demonstrates improvement.

No algorithm can guarantee the best future player from this dataset. The testable claim is whether a method selects players who subsequently perform better than the alternatives under the predeclared evaluation.

## 3. P0: repair the data contract before changing rankings

Implement `backend/analytics/data_validation_v2.py` and `scoreboard_v2.py`.

1. Keep original sources immutable. Retain physical source rows, match IDs, player IDs, source version and correction provenance.
2. Give each match/innings a quality record: event ordering, missing events, known legal deliveries, extras semantics, dismissals, allocated balls, innings ending, revisions and field availability.
3. Adjudicate the 11 flagged innings. Check reduced allocations, DLS/revisions, retired-hurt/unavailable batters and genuine truncation. Result text may flag a quality review; it must not determine a pre-ball pressure label.
4. Check over-ID continuity, the start of innings, whole-over counts and completion against verified rules. A normal-looking final over is insufficient proof of complete data.
5. Track exclusions by season, role, player and competition. Compare included and excluded exposure to reveal possible selection effects.
6. Preserve usable facts at field level. Do not discard an entire innings unnecessarily, but do not use uncertain balls-remaining or score state merely because off-bat outcomes are known.

Use explicit data modes:

| Mode | Verified fields | Permitted claims |
|---|---|---|
| Full scoreboard | Exact extras, legal-ball sequence, score, allocated balls and chase target where applicable | Score-state analysis and the appropriate complete bowling statistics, with proper attribution |
| Limited context | Trusted off-bat outcomes, wickets, phase/allocation where known, identity and opponents | Clearly named proxy analysis; no fabricated RRR, full economy or win-probability impact |
| Unresolved | Ambiguous sequence, allocation, identity or key outcome | Quality-review queue; only independently trustworthy summaries |

Do not combine scores from differently defined estimands into one list without a common comparison basis. Report full-scoreboard and limited-context sensitivity on matched cohorts.

If RR can supply the original extras quantities or a schema correction, use that first. Otherwise, a local reconciliation with an authoritative public source is a candidate recovery path. Cricsheet JSON represents batter runs, extras, total runs, individual extras types, and innings target information; actual overlap and completeness must be checked. It is not a guaranteed repair for every proprietary match. [Cricsheet format](https://cricsheet.org/format/json/), [available downloads](https://cricsheet.org/downloads/).

Cross-source matches need verified date, teams, competition and innings alignment, with player-ID aliases and delivery-sequence checks. Do not merge on names alone or add the same match twice. Store a recovered field separately from the original value and record its source. Never upload the proprietary pack to perform this reconciliation.

**Acceptance:** every flagged innings has a recorded decision; every score-state input has verified provenance; unresolved fields remain missing; no unexplained scorecard mismatches or duplicate match contributions enter a ranking run.

## 4. P1: compare cricket roles on the same task

Implement `features_v2.py` and a role/context specification.

Batting roles should distinguish opening/top order, middle-order rebuilding, finishing and tail batting. Bowling roles should describe actual powerplay, middle-over and death-over workload, with pace/spin as an additional characteristic. Bowling style alone is not a phase role. Allow a player to have more than one role with distinct evidence.

Use roles and opponent ratings available at the evaluation cutoff. A future career batting-position median or an opponent rating calculated using the test match must not enter an earlier prediction.

Context candidates, subject to coverage:

- Innings, known allocated balls, phase, wickets/resources, batting position and handedness.
- Exact score, target, required rate and rate relative to a contextual benchmark only in full-scoreboard mode.
- Competition, season scoring environment, venue and innings conditions where recorded.
- Opponent batter/bowler quality estimated from preceding matches, with partial pooling for sparse evidence.
- Pace/spin matchup and established batter/partnership context.

Standardize players onto a fixed, documented distribution of opportunities for the role. A finisher and an opener should not receive different scores simply because one encountered more of the model's chosen stress situations. Keep within-role rankings and a category-wide comparison in common units; do not compare role percentiles as if they were absolute performance values.

**Acceptance:** the same role/task produces comparable opportunities; a player with no evidence in an unplayed phase receives an evidence-gap flag, not a zero or invented versatility bonus.

## 5. P1: replace pressure cliffs with explainable situation signals

Implement `pressure_v2.py` with continuous signals and readable situation labels.

Keep at least four separate concepts:

1. **Resource stress:** wickets and batting resources relative to the remaining allocation.
2. **Scoring difficulty:** required scoring relative to an expected rate, where exact chase state is verified.
3. **Competitive leverage:** how much plausible next-ball outcomes can change the contest, based on a calibrated state model fitted on preceding data.
4. **Stage/stakes:** knockout or other verifiable pre-match context, with conservative treatment of sparse knockout evidence.

A nearly impossible chase can be difficult yet have low competitive leverage. A tight achievable finish can have high leverage. These should not collapse into one arbitrary binary indicator. Also distinguish rebuild/collapse pressure, close-chase finishing, defending a competitive target and bowling against established batting.

For a validated chase win model, `4p(1-p)` is a candidate closeness signal. It is not a complete pressure measure: two states with the same win chance can have different next-ball leverage. Estimate leverage from the distribution of possible next outcomes before the delivery, not from the outcome that actually happened. First-innings analysis needs a separately validated remaining-runs or match-state model; never invent an unknown target.

In limited-context mode, retain observable resource and established-batting signals. Label them as proxies and test them separately. Do not claim a win-probability calculation when inputs or calibration are insufficient.

**Acceptance:** changing the current delivery or eventual result cannot alter its pre-delivery signals. Small state changes produce proportionate signal changes. A scenario report demonstrates plausible behaviour for collapses, comfortable chases, close finishes and reduced allocations.

## 6. P2: estimate ability and pressure performance with partial pooling

Implement `context_models_v2.py` and `player_model_v2.py`.

Start with a regularized contextual model for recorded scoring outcomes and a separate dismissal/credited-wicket model. Evaluate a more flexible model only as a challenger. Model complexity is justified by held-out results, not by the number of features or algorithms.

For historical descriptive assessment, use predictions from a model that did not fit the evaluated match. For forecasting, fit on preceding data and apply the frozen artifact to the next period. All preprocessing, opponent ratings, priors and tuning obey the same cutoff.

On top of contextual expectations, estimate:

- General player ability in the specified role.
- Pressure-specific change in that ability, with a prior centered near no additional pressure effect.
- Recent change in form, if it adds repeatable held-out information.
- Variation across comparable pressure innings or spells.

A player can be excellent under pressure without an identifiable special clutch trait. Shrink a noisy pressure interaction strongly rather than rewarding an unreliable lift. High absolute pressure performance should matter more than improvement from a weak personal baseline.

Use empirical-Bayes or hierarchical partial pooling to pull sparse observations toward the relevant role/competition expectation. Choose shrinkage strength on training folds; do not assume the current 120/240-ball constants are optimal. If a full hierarchical model is added, use an appropriate likelihood and check approximation/posterior diagnostics before trusting its intervals.

Test recency using an explicit cutoff and a small predeclared range of time-decay settings, such as 180, 365 and 730 days. These are candidate half-lives, not validated recommendations. Report effective innings/balls and raw counts separately. Repeated deliveries in one match do not create the same information as independent matches.

Remove the separate sample-size bonus from performance quality. Sample support should govern shrinkage, uncertainty and eligibility. A large sample alone is not evidence of high-quality cricket.

**Acceptance:** rare players do not obtain extreme certainty from a small sample; pressure interactions shrink when unsupported; stronger simple baselines are retained if a complex candidate fails to improve the evaluation.

## 7. P2: replace correlated component sums with a defensible value estimate

Implement `reliability_v2.py`.

Estimate role-standardized pressure value above an explicitly defined replacement/peer benchmark. Use a documented opportunity unit, such as 100 comparable legal deliveries. Produce separate batting and bowling estimates.

The current constant 12-run wicket price should not be represented as a measured universal cricket value. In full-scoreboard mode, estimate state-dependent resource value using an independent training-only model of remaining runs or match value. In limited-context mode, retain scoring and wicket/survival estimates as separate axes; if a scalar decision score is required, disclose and stress-test its trade-off assumption.

For player `i` in role `r`, the candidate ranking quantity is:

```text
V(i, r) = expected pressure value above the role benchmark
          on a fixed distribution of comparable opportunities

Conservative value(i, r) = lower posterior quantile of expected V(i, r)
```

The quantile reflects a selection risk preference. Evaluate, for example, the posterior mean and a conservative lower quantile as separate policies. A 10th-percentile choice is a candidate policy, not a scientifically optimal constant.

Distinguish uncertainty about a player's expected ability from the randomness of their next innings. Show posterior uncertainty, the predicted chance of a below-benchmark pressure contribution, and sample support separately. A single lower percentile of next-innings outcomes can otherwise penalize an attacking role for its normal variance.

Avoid counting the same scoring and survival residual repeatedly in pressure, adaptability and efficiency components. Keep such views as explanations of the underlying estimate rather than independent bonuses.

If the product requires 0-100 scores, map the final value against a frozen, documented reference cohort. Label the result as an index, not a probability. Preserve underlying values and intervals so users can see near ties. Produce a discovery/watchlist view for promising players whose samples are insufficient for the main ranking.

**Acceptance:** the value measure, its units, benchmark and risk preference are explicit; missing information never becomes a zero or a bonus; the ranking is reproducible without manual player-specific overrides.

## 8. P3: establish whether selection actually improves

Implement `backtest_v2.py` before promoting any score into the submission report.

Use rolling, whole-match chronological folds, for example 2022 to 2023, 2022-23 to 2024, 2022-24 to 2025 and 2022-25 to available 2026 data. Group same-date fixtures conservatively when precise timestamps are unavailable. Fit transformations and tune parameters using inner chronological folds only. Ordinary random ball splitting would mix observations from the same matches and from later periods. [scikit-learn cross-validation guidance](https://scikit-learn.org/stable/modules/cross_validation.html).

Replace the hardcoded activity year and the training-year overwrite with `as_of_date` and configurable trailing activity windows. Eligibility must use training information only. Evaluation-period appearances are used to report evaluation coverage, never to select an easier candidate population in advance. A player with no future observation is unobserved, not a zero performer.

The 2025-2026 results have already been examined while designing this improvement. Historical rolling tests remain useful, but those years must be called reused holdouts. Reserve newly arriving data for a genuinely untouched prospective confirmation.

Compare at least:

| Baseline/candidate | What it tests |
|---|---|
| Current v1 score | Whether the replacement improves the actual existing system |
| Recent role-adjusted scoring and survival/wicket rates | Whether complexity adds value beyond recent observed quality |
| Empirical-Bayes role model without a pressure interaction | Whether there is useful repeatable information in the pressure-specific effect |
| V2 contextual and partially pooled candidate | Whether the full proposal improves the declared task |

Evaluation must include:

- Proper outcome losses for scoring distributions and dismissal/wicket predictions.
- Calibration plots and reliability diagnostics alongside Brier/log loss. Those losses combine calibration and discrimination; lower loss alone does not prove better calibration. [scikit-learn calibration guidance](https://scikit-learn.org/stable/modules/calibration.html).
- Future role-adjusted pressure performance of the selected top 10, versus the same eligible baseline populations.
- Rank correlation and selection regret/uplift with uncertainty, not just top-10 membership stability.
- Performance by role, season, competition, exposure level and data-quality mode.
- Pressure-definition, recency, prior-strength and wicket-trade-off sensitivity.
- IPL-only evaluation and explicit international-to-IPL transfer checks, rather than assuming T20I and IPL are equivalent.

Do not optimize a model solely to reproduce its own constructed score or a preferred set of famous players. Do not choose the pressure definition that makes the final rankings look most plausible after looking at the test results.

**Promotion rule:** predeclare a primary metric and acceptable calibration/coverage margins. Require improvement over the strongest simple baseline across rolling folds, supported by paired uncertainty analysis, with no unexplained role-specific collapse. An inconclusive interval means no established superiority. If v2 loses, retain the stronger model and publish the result of the comparison.

## 9. P3: improve uncertainty and ranking stability

Implement `uncertainty_v2.py`.

Resample whole matches jointly for all involved players when assessing rank uncertainty, preserving opposition and shared conditions. For estimation uncertainty, refit the relevant expectations and player estimates within each replicate where feasible. Reapply the predefined candidate/eligibility policy rather than secretly fixing a favourable cohort.

Keep different uncertainties separate:

- Posterior/estimation uncertainty under a declared model.
- Predictive variability of the next contribution.
- Sensitivity to pressure definitions, data repair and role distributions.
- Source coverage and unverified external facts.

Show median rank, plausible rank range, pairwise superiority and top-10 membership probability only when supported by an appropriate joint simulation or refit distribution. Current weight-scenario frequencies must remain labelled as weight sensitivity, not as probabilities that a player belongs in the true top 10.

**Acceptance:** uncertainty grows when matches are removed or source quality deteriorates; low-sample discoveries remain visible without being presented as certain elite performers.

## 10. P4: expose the new evidence in the local app and report

Keep the current React/FastAPI architecture. Prioritize analytical correctness before visual changes.

- Add explicit views for historical pressure reliability, role fit, and RR scouting feasibility.
- Show pressure value, uncertainty, role, recency, raw/effective opportunities, source mode and the reason for selection.
- Display pressure and non-pressure performance after matching/standardizing context; keep raw numbers available.
- Show player availability as verified, unavailable or unknown with a source and check date. Unknown must not mean available.
- Return an explicit insufficient-evidence state instead of inventing a ranking for an empty or tiny subset.
- If season/competition filters are advertised as recalculating results, aggregate the selected observations against a declared frozen model and prior. The present coverage filters do not do this.
- Include a model-comparison page showing v1 and candidate backtests, including failed experiments.
- Export the PDF, CSV and dashboard snapshot from one run manifest. Publish the new local snapshot atomically only after its validation and report succeed. Do not replace the accepted output while an experiment is incomplete.

## 11. Build order and reviewable deliverables

| Order | Work | Principal planned files | Completion evidence |
|---|---|---|---|
| 1 | Freeze v1 and specify the target | Experiment config and versioned run manifest | Reproducible current output and written evaluation contract |
| 2 | Adjudicate data defects | `data_validation_v2.py`, `scoreboard_v2.py` | Quality register, the 11 reviewed innings, reconciled field provenance |
| 3 | Build time-safe features and pressure signals | `features_v2.py`, `pressure_v2.py` | Scenario checks, no future/current-ball leakage, allocation-aware phase handling |
| 4 | Establish strong simple baselines | `backtest_v2.py`, baseline estimators | Rolling baseline results before tuning the challenger |
| 5 | Fit context and player models | `context_models_v2.py`, `player_model_v2.py` | Out-of-fold expectations, partial pooling and recency ablations |
| 6 | Rank with uncertainty | `reliability_v2.py`, `uncertainty_v2.py` | Common-unit role values, rank uncertainty and sensitivity reports |
| 7 | Compare, then adopt or reject | Evaluation manifest and comparison report | Passed predeclared promotion criteria, or an explicit decision to retain the stronger baseline |
| 8 | Refresh the local product | API schemas, React views, report builder | Identical model version/rankings across app, CSV and PDF |

## 12. Required verification cases

- A bye/leg-bye changes the team score but is not a bowler-conceded run; wides/no-balls and legal-ball counts follow verified event semantics.
- A non-striker run-out is not charged as a striker dismissal or credited as a bowler wicket.
- A successful chase ending early does not shorten the known scheduled allocation; a genuinely reduced innings uses its verified allocation.
- A retired-hurt ending is not automatically classified as missing data or an ordinary all-out.
- Changing a final result or the current delivery cannot change that delivery's pre-ball pressure inputs.
- Future matches cannot alter an earlier as-of feature, prior, eligibility decision or opponent rating.
- Small samples shrink toward their relevant prior; missing metrics and legitimate zeros remain distinct.
- Joint resampling preserves shared match conditions across the players being compared.
- Pure proxy data cannot produce a full-economy or exact-RRR label.
- Backend filters use the displayed period and an explicit evidence policy; empty subsets produce an honest unavailable result.
- Every export has the same run ID and agrees with the accepted analysis; experiments cannot overwrite it partway through computation.

The immediate implementation priority is the data-quality register and a correct rolling baseline evaluation. A new final top 10 is justified only after those steps and the candidate comparison are complete.
