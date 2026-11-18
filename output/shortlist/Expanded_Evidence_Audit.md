# Pressure reliability: expanded evidence audit

Uses all six source files through the validated pipeline. No extra fields are treated as score inputs merely because they exist.

Full-match removal checks whether a player depends on one result. Context breakdowns cover season, competition, phase, venue country, pace/spin, handedness and knockouts. These small-sample slices are descriptive and do not establish causal matchup effects.

For batting, pace/spin describes the opposing bowler; for bowling it describes the player. Handedness describes the striker in both cases.

Match success uses at least three high-pressure balls per match and Beta(2,2) smoothing. It is a consistency diagnostic, not a match-winning probability.

The current ranking remains historical. Existing next-season comparisons do not justify a claim of superior forecasts. New features are evidence checks rather than unvalidated score bonuses.

## Batters

| Rank | Player | High matches | Largest match share | Point | Worst removal | Flags |
|---:|---|---:|---:|---:|---:|---|
| 1 | Mahendra Singh Dhoni | 17 | 13% | +3.18 | +2.66 | No single-match flag |
| 2 | Faf du Plessis | 9 | 24% | +1.80 | +0.86 | No single-match flag |
| 3 | Dinesh Karthik | 23 | 14% | +1.85 | +0.97 | No single-match flag |
| 4 | Rashid Khan | 32 | 11% | +1.70 | +0.60 | No single-match flag |
| 5 | Ravindra Jadeja | 35 | 8% | +0.73 | +0.51 | No single-match flag |
| 6 | Basil Hameed | 5 | 39% | +0.77 | -0.09 | One match supplies over 35% of pressure balls; Positive impact turns negative after removing a match |
| 7 | Haider Ali | 4 | 38% | +0.34 | -0.23 | One match supplies over 35% of pressure balls; Positive impact turns negative after removing a match |
| 8 | Virat Kohli | 14 | 21% | +0.17 | -0.40 | Positive impact turns negative after removing a match |
| 9 | Abdul Samad | 21 | 16% | +0.00 | -0.51 | Positive impact turns negative after removing a match |
| 10 | Shikhar Dhawan | 8 | 36% | -0.99 | -1.73 | One match supplies over 35% of pressure balls |

## Bowlers

| Rank | Player | High matches | Largest match share | Point | Worst removal | Flags |
|---:|---|---:|---:|---:|---:|---|
| 1 | Amit Mishra | 5 | 25% | +1.73 | +0.93 | No single-match flag |
| 2 | Dwayne Bravo | 5 | 30% | +1.38 | +0.48 | No single-match flag |
| 3 | Haider Ali | 6 | 32% | +1.41 | +0.12 | No single-match flag |
| 4 | Rashid Khan | 74 | 3% | +0.94 | +0.60 | No single-match flag |
| 5 | Ishant Sharma | 9 | 21% | -0.16 | -0.97 | No single-match flag |
| 6 | Piyush Chawla | 13 | 20% | -1.93 | -2.69 | No single-match flag |
| 7 | Ravindra Jadeja | 32 | 7% | -1.99 | -2.46 | No single-match flag |
| 8 | Muhammad Farooq | 3 | 58% | +0.97 | +0.05 | One match supplies over 35% of pressure balls; Fewer than four pressure matches |
| 9 | Basil Hameed | 3 | 53% | -0.42 | -0.94 | One match supplies over 35% of pressure balls; Fewer than four pressure matches |
| 10 | Bashir Ahmad | 1 | 100% | -1.53 | Unavailable | One match supplies over 35% of pressure balls; Fewer than four pressure matches |

## Coverage limits

The pack cannot recover primary extras amounts, exact running totals, reliable required run rates or win probabilities. Final results are used only for quality checks. Awards, player names and roster membership are not performance predictors. Raw files remain unchanged.

The 20-name restriction excludes other potentially stronger players. Name collisions remain explicit: Pakistan Haider Ali is the batter; UAE Haider Ali is the bowler. Auction eligibility is unverified.
