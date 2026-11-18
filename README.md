# SupeRR Selector — Rajasthan Royals scouting dashboard

A React and TypeScript dashboard for the SupeRR Selector Season 2 pressure-performance challenge. It presents the final top ten batters and bowlers from the user's screenshot pool, with Mahendra Singh Dhoni excluded by request.

[Open the dashboard](https://mayank2142.github.io/RR/) · [Download the report](https://mayank2142.github.io/RR/report.pdf) · [Download the selections](https://mayank2142.github.io/RR/selections.csv)

## Dashboard

The dashboard includes player rankings, pressure and non-pressure comparisons, source-match evidence, sample sizes, uncertainty intervals, a data audit and PDF/CSV downloads. User-supplied Rajasthan Royals photos appear in the hero and gallery. The palace poster responds to pointer movement with a 3D tilt, with reduced-motion support.

The hosted page is a self-contained React build with embedded results, photographs and downloads. It can run on GitHub Pages without an API or database. The optional FastAPI backend supports the earlier whole-pack research workspace.

## Results and evidence

The current snapshot assesses 181,174 validated legal deliveries through 1 November 2026. A match crosswalk verifies 668 public Cricsheet games against the RR pack, recovers 11,735 extras runs and restores 22,506 legal balls. Scoreboard pressure uses targets, pre-delivery score, wickets in hand and balls remaining where verified. Validated proxy context covers other games.

The output is restricted to 19 eligible screenshot names. Haider Ali is Pakistan player ID 7338 in batting and UAE player ID 28756 in bowling. Bowlers ranked 8–10 have provisional evidence. Player registration, fitness, retirement and auction availability require separate verification. The historical ratings have mixed later-season validation results.

## Run the dashboard

Use Node.js 22 or later.

```sh
npm ci
npm run dev
```

Open the URL printed by Vite, normally `http://127.0.0.1:5173/`.

```sh
npm run build
npm run build:pages
```

The Pages build writes `site/index.html`, `site/report.pdf` and `site/selections.csv`. The self-contained dashboard is also available as `output/shortlist/SupeRR_Shortlist_Dashboard.html` and opens directly in a browser.

## Project files

| Folder | Contents |
| --- | --- |
| `frontend/src/` | React dashboard, comparison and profile views, styles and 3D interaction |
| `frontend/public/` | Computed snapshots, PDF, selections and four supplied photographs |
| `backend/analytics/` | Data validation, context reconstruction, public-match alignment and scoring |
| `scripts/` | Analysis experiments, final selection exports, PDF and portable-site builders |
| `tests/` | Scoreboard, identity, scoring and export consistency checks |
| `output/shortlist/` | Final snapshot, selections and public-match crosswalk |
| `output/pdf/` | Final report and historical research reports |
| `.github/workflows/` | Automatic GitHub Pages deployment on pushes to `main` |

Earlier whole-pack artifacts are retained as research history. The current report is `output/pdf/SupeRR_Screenshot_Shortlist_Report.pdf`, and the current selections are `output/shortlist/Shortlist_Form_Selections.csv`.

## Reproduce the analysis

Python 3.11 or later is required for analytics. Install `backend/requirements-analytics.txt`. The original RR data pack must be supplied locally in `6af3166e7b922_data_pack/`. It is excluded from the repository. Public Cricsheet archives can be downloaded into `tmp/cricsheet/`.

```sh
python -m pip install -r backend/requirements-analytics.txt
python scripts/scoreboard_shortlist.py
python scripts/finalize_scoreboard.py
python scripts/build_shortlist_report.py
npm run build:pages
```

The PDF builder uses Segoe UI fonts on Windows. The committed report allows dashboard deployment on Linux without regenerating it.

The local tests that inspect the original RR pack require that pack to be present. The GitHub workflow checks TypeScript and builds the app and Pages artifact from the committed snapshot.

## Deployment

GitHub Actions builds the project and deploys to GitHub Pages on each push to `main`. The workflow can also be started from the Actions tab. Repository Pages settings use GitHub Actions as the publishing source.

## Sources and photographs

Cricsheet public archives and schema are available at [Cricsheet downloads](https://cricsheet.org/downloads/) and [JSON format](https://cricsheet.org/format/json/). Accepted and rejected local-match joins are recorded in `output/shortlist/Cricsheet_Match_Crosswalk.csv`.

The photographs were supplied by the user. The interface takes visual cues from [Rajasthan Royals](https://www.rajasthanroyals.com/). This is independent competition analysis. Team imagery and trademarks belong to their respective owners.
