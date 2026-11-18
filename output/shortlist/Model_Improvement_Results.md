# Stronger approach: test before changing ranks

The experiment compares five methods on common players: the published conservative score, usual ability, pressure-only ability, pressure ability shrunk toward usual performance, and the pooled method with a two-year recency half-life.

Pooling removes the bonus a weak usual baseline can give the old lift term. Recency is a candidate assumption, not an automatic improvement. Existing peer expectations exclude the player and are fitted only on preceding years.

Method selection uses earlier validation years. The 2025 and 2026 evaluation compares with the best simple baseline selected from earlier years. A paired player-cluster bootstrap measures uncertainty in the average correlation gain. All years have already been inspected in this project, so this is retrospective evidence, not a pristine final test.

## bat

| Test year | Players | Published | Usual | Pressure | Pooled | Recent pooled |
|---|---:|---:|---:|---:|---:|---:|
| 2024 | 62 | +0.032 | +0.117 | +0.084 | +0.164 | +0.110 |
| 2025 | 75 | +0.022 | +0.204 | +0.019 | +0.059 | +0.042 |
| 2026 | 71 | -0.047 | +0.258 | -0.100 | +0.051 | +0.105 |

Nested mean gain: -0.073; paired 95% interval: -0.180 to +0.044.
Promotion screen: not passed; retain the published descriptive ranking

- 2025: earlier data selected pooled; baseline usual.
- 2026: earlier data selected usual; baseline usual.
## bowl

| Test year | Players | Published | Usual | Pressure | Pooled | Recent pooled |
|---|---:|---:|---:|---:|---:|---:|
| 2024 | 64 | -0.170 | +0.053 | -0.183 | -0.125 | -0.131 |
| 2025 | 74 | +0.009 | -0.105 | +0.003 | -0.044 | -0.006 |
| 2026 | 57 | +0.087 | +0.034 | +0.105 | +0.109 | +0.105 |

Nested mean gain: +0.000; paired 95% interval: +0.000 to +0.000.
Promotion screen: not passed; retain the published descriptive ranking

- 2025: earlier data selected usual; baseline usual.
- 2026: earlier data selected usual; baseline usual.

## Next decision

Do not combine highly correlated features into extra score bonuses. Keep context slices and single-match removal as diagnostic evidence. Expand only with verified scoreboard/extras data and more repeated pressure matches; never infer missing required run rates or availability. The 20-name screenshot pool remains the output constraint.

The primary historical submission measures pressure performance and change versus usual performance. A model predicting later performance is a separate research question; even a forecasting winner cannot silently redefine that submission objective.
