import { useRef, useState } from 'react';
import { motion, useMotionValue, useSpring, useTransform, useReducedMotion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import * as Dialog from '@radix-ui/react-dialog';
import { Activity, ArrowRight, ChartNoAxesColumn, ClipboardList, Database, Download, FileText, Search, ShieldCheck, Swords, Target, X } from 'lucide-react';
import type { Category } from './types';
import './shortlist.css';

type Tier = 'Substantial' | 'Supporting' | 'Provisional' | 'Unrated';
type Stats = { balls: number; runs: number; outs: number; rate: number | null; adjusted_impact: number | null };
type Estimates = { usual: number; pressure: number; lift: number; point: number; score: number | null; low: number | null; high: number | null };
type Example = Stats & { match_id: number; innings: number; date: string; competition: string; source_rows: number[]; pressure_reasons: string[] };
type Row = {
  name: string; id: number; affiliation: string; rank: number | null; role: string;
  tier: Tier; reason: string; identity_ambiguous: boolean; estimates: Estimates | null;
  sample: { balls: number; high_balls: number; innings: number; high_innings: number; high_matches: number; last_seen: string | null };
  high: Stats; non_high: Stats; phases: (Stats & {phase: string; high_balls: number})[]; examples: Example[];
  competitions: string[]; rr_note: string;
};
type Side = { ranking: Row[]; candidates: Row[] };
type Fold = { scope: string; test_year: number; train_through: number; common_players: number; proposed: number | null; legacy: number | null };
type Snapshot = {
  version: string; build_id: string; source_cutoff: string; source_start: string;
  scoreboard_audit: { verified_matches: number; verified_extras_runs: number; restored_legal_balls: number };
  categories: Record<Category, Side>;
  identities: Record<string, { id: number; teams: string[]; used_for: Category[] }[]>;
  method: { wicket_value: number; bootstrap_draws: number; gates: Record<Category, Record<string, number[]>> };
  audit: {
    accepted_legal_balls: number; accepted_matches: number; accepted_innings: number;
    source_files: Record<string, { rows: number; columns: number; repeated_keys?: number }>;
    join_coverage: Record<string, number>; families: Record<string, number>;
    excluded_extra_review: { additional_dls_legal_balls_quarantined: number; additional_ambiguous_legal_balls_quarantined: number; unresolved_match_ids: number[] };
  };
  validation: {
    sensitivity: Record<Category, { scenario: string; ranked: number; overlap: number; shifts: {player: string; base: number; scenario: number | null}[] }[]>;
    chronological: Record<Category, Fold[]>;
    legacy_holdout: Record<Category, { spearman: number; common_players: number }>;
  };
};

const kinds = ['bat', 'bowl'] as const;
const discipline = { bat: 'Batting', bowl: 'Bowling' };
const int = (value: number) => new Intl.NumberFormat('en-IN').format(value);
const metric = (value: number | null | undefined, digits = 2) => value == null ? '—' : value.toFixed(digits);
const signed = (value: number | null | undefined) => value == null ? '—' : `${value > 0 ? '+' : ''}${value.toFixed(2)}`;
const rateLabel = (kind: Category) => kind === 'bat' ? 'Runs per 100 legal balls' : 'Off-bat runs per six legal balls';
const outs = (kind: Category) => kind === 'bat' ? 'Striker dismissals' : 'Credited wickets';
const report = '/SupeRR_Screenshot_Shortlist_Report.pdf';
const exportFile = '/Shortlist_Form_Selections.csv';
const countTier = (side: Side, tier: Tier) => side.ranking.filter(p => p.tier === tier).length;
const offline = Boolean(document.getElementById('sl-snapshot'));
const sections = [{label: 'Rankings', Icon: ClipboardList}, {label: 'Compare', Icon: ChartNoAxesColumn},
  {label: 'Data & method', Icon: Database}] as const;
type Section = typeof sections[number]['label'];

function localDownload(selector: string, fallback: string, mime: string) {
  const embedded = document.getElementById(selector)?.textContent?.trim();
  if (!embedded) return fallback;
  const data = Uint8Array.from(atob(embedded), ch => ch.charCodeAt(0));
  return URL.createObjectURL(new Blob([data], {type: mime}));
}

const reportLink = localDownload('sl-report', report, 'application/pdf');
const selectionsLink = localDownload('sl-selections', exportFile, 'text/csv');
const photo = (name: string) => document.getElementById(`sl-photo-${name}`)?.textContent?.trim() || `/rr/${name}.png`;

function RoyalsHero() {
  const reduced = useReducedMotion();
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const rotateX = useSpring(useTransform(y, [-.5, .5], [5, -5]), {stiffness: 110, damping: 25});
  const rotateY = useSpring(useTransform(x, [-.5, .5], [-6, 6]), {stiffness: 110, damping: 25});
  return <section className="rr-hero" onPointerMove={event => {
    if (reduced || event.pointerType === 'touch') return;
    const bounds = event.currentTarget.getBoundingClientRect();
    x.set((event.clientX-bounds.left)/bounds.width-.5);
    y.set((event.clientY-bounds.top)/bounds.height-.5);
  }} onPointerLeave={() => { x.set(0); y.set(0); }}>
    <img className="rr-hero-photo" src={photo('team')} alt="Rajasthan Royals teammates celebrate a wicket"/>
    <div className="rr-hero-shade"/>
    <div className="rr-hero-copy"><span className="sl-kicker">SupeRR Selector · Season 2</span>
      <h1>THE ROYALS<br/><em>SCOUTING ROOM.</em></h1>
      <p>Find your next pressure player. Explore the evidence behind every selection.</p>
      <div className="sl-hero-actions"><a className="sl-button sl-primary" href={reportLink} download={report.slice(1)}><FileText size={17}/>Download report</a>
        <a className="sl-button sl-secondary" href={selectionsLink} download={exportFile.slice(1)}><Download size={17}/>Top 10 selections</a></div>
    </div>
    <motion.div className="rr-poster" style={reduced ? {} : {rotateX, rotateY, transformPerspective: 1000}}>
      <img src={photo('royals-palace')} alt="Royals of 2026 team poster at a Rajasthan palace"/>
      <span>HALLA BOL.</span>
    </motion.div>
  </section>;
}

async function load(): Promise<Snapshot> {
  const embedded = document.getElementById('sl-snapshot')?.textContent;
  if (embedded) return JSON.parse(embedded);
  const res = await fetch('/shortlist.json', { cache: 'no-cache' });
  if (res.ok && res.headers.get('content-type')?.includes('json')) return res.json();
  throw new Error('Shortlist results are unavailable. Rebuild the local data before opening the dashboard.');
}

function TierBadge({ tier }: { tier: Tier }) {
  return <span className={`sl-badge sl-${tier.toLowerCase()}`}>{tier}</span>;
}

function RankTable({ side, kind, search, onPlayer }: { side: Side; kind: Category; search: string; onPlayer: (row: Row, kind: Category) => void }) {
  const filtered = side.ranking.filter(row => row.name.toLowerCase().includes(search) || row.affiliation.toLowerCase().includes(search));
  const Icon = kind === 'bat' ? Swords : Target;
  return <section className="sl-card sl-ranking">
    <header className="sl-card-title">
      <span className="sl-icon"><Icon size={19} /></span>
      <div><h2>Top {kind === 'bat' ? 'batters' : 'bowlers'}</h2><p>{side.ranking.length} of 10 slots filled · {countTier(side, 'Provisional')} provisional</p></div>
    </header>
    <div className="sl-table-scroll">
      <table>
        <thead><tr><th scope="col">Rank</th><th scope="col">Player</th><th scope="col">High balls</th><th scope="col">Score / evidence</th></tr></thead>
        <tbody>{filtered.map(row => <tr key={row.id}>
          <td className="sl-rank">{String(row.rank).padStart(2, '0')}</td>
          <th scope="row"><button className="sl-player" onClick={() => onPlayer(row, kind)}>{row.name}</button><small>{row.identity_ambiguous ? row.affiliation : row.role}</small></th>
          <td className="sl-num">{int(row.sample.high_balls)}</td>
          <td><strong className="sl-score-value">{signed(row.estimates?.score)}</strong><TierBadge tier={row.tier} /><small>{row.sample.last_seen ?? "No sample"}</small></td>
        </tr>)}</tbody>
      </table>
      {filtered.length === 0 && <p className="sl-empty">No ranked names match this search.</p>}
    </div>
  </section>;
}

function EvidencePairs({ row, kind }: { row: Row; kind: Category }) {
  const metrics: [string, string, string][] = [
    ['Legal balls', int(row.high.balls), int(row.non_high.balls)],
    ['Off-bat runs', int(row.high.runs), int(row.non_high.runs)],
    [outs(kind), int(row.high.outs), int(row.non_high.outs)],
    [rateLabel(kind), metric(row.high.rate), metric(row.non_high.rate)],
    ['Adjusted run equivalents per six', signed(row.high.adjusted_impact), signed(row.non_high.adjusted_impact)],
  ];
  return <table className="sl-detail-table"><thead><tr><th scope="col">Observed evidence</th><th scope="col">High</th><th scope="col">Non-high</th></tr></thead>
    <tbody>{metrics.map(([k, a, b]) => <tr key={k}><th scope="row">{k}</th><td>{a}</td><td>{b}</td></tr>)}</tbody></table>;
}

function PlayerDialog({ row, kind, onClose }: { row: Row; kind: Category; onClose: () => void }) {
  const e = row.estimates;
  return <Dialog.Root open onOpenChange={open => { if (!open) onClose(); }}>
    <Dialog.Portal>
      <Dialog.Overlay className="sl-overlay" />
      <Dialog.Content className="sl-dialog sl-surface" onCloseAutoFocus={event => event.preventDefault()}>
        <div className="sl-dialog-head">
          <span className="sl-kicker">{discipline[kind]} {row.rank ? ` · rank ${row.rank}` : ' · candidate'}</span>
          <Dialog.Title>{row.name}</Dialog.Title>
          <Dialog.Description>{row.affiliation} · Source ID {row.id}</Dialog.Description>
          <Dialog.Close className="sl-close" aria-label="Close player profile"><X size={20} /></Dialog.Close>
        </div>
        <div className="sl-dialog-body">
          <p className="sl-inline"><TierBadge tier={row.tier} /><span>{row.role} · Last in sample {row.sample.last_seen ?? '—'}</span></p>
          {row.identity_ambiguous && <p className="sl-warning">The source contains more than one ID with this name. Confirm the team and player before using a bare dropdown label.</p>}
          <p>{row.rr_note} {row.reason}.</p>
          <div className="sl-mini-metrics">
            <div><span>Ordering score</span><strong>{signed(e?.score)}</strong></div>
            <div><span>Pressure lift vs usual</span><strong>{signed(e?.lift)}</strong></div>
            <div><span>95% conditional interval</span><strong>{e?.low != null ? `${signed(e.low)} to ${signed(e.high)}` : 'Unavailable'}</strong></div>
          </div>
          <p className="sl-note">Score and interval use adjusted run equivalents per six balls. A larger number means better performance than context peers. Intervals are conditional on this analysis.</p>
          <EvidencePairs row={row} kind={kind} />
          <h3>Opportunity by phase</h3>
          <div className="sl-phases">{row.phases.map(p => <div key={p.phase}><strong>{p.phase}</strong><span>{int(p.high_balls)} high / {int(p.balls)} legal balls</span>
            <progress aria-label={`${p.phase}: high-pressure share`} value={p.high_balls} max={Math.max(p.balls, 1)} /></div>)}</div>
          <h3>Match evidence</h3>
          {row.examples.length === 0 && <p className="sl-note">No validated high-pressure match examples.</p>}
          {row.examples.map(example => <div key={`${example.match_id}:${example.innings}`} className="sl-example">
            <strong>{example.competition} · {example.date}</strong>
            <p>{int(example.balls)} high balls · {example.runs} off-bat runs · {example.outs} {outs(kind).toLowerCase()}</p>
            <p>{example.pressure_reasons.join(' · ')}</p>
            <small>Match {example.match_id} · Innings {example.innings} · Original CSV rows {example.source_rows.join(', ')}</small>
          </div>)}
        </div>
      </Dialog.Content>
    </Dialog.Portal>
  </Dialog.Root>;
}

function Comparison({ data }: { data: Snapshot }) {
  const [kind, setKind] = useState<Category>('bat');
  const [ids, setIds] = useState<[number, number] | null>(null);
  const choices = data.categories[kind].ranking;
  if (choices.length < 2) return <p className="sl-card sl-empty">This discipline does not have two rated candidates to compare.</p>;
  const [a, b] = (ids ?? [choices[0].id, choices[1].id]).map(id => choices.find(p => p.id === id) ?? choices[0]);
  const cells: [string, string, string][] = [
    ['Evidence', a.tier, b.tier],
    ['Last qualifying appearance', a.sample.last_seen ?? '—', b.sample.last_seen ?? '—'],
    ['High-pressure balls', int(a.sample.high_balls), int(b.sample.high_balls)],
    ['Distinct high-pressure matches', int(a.sample.high_matches), int(b.sample.high_matches)],
    [`High: ${rateLabel(kind).toLowerCase()}`, metric(a.high.rate), metric(b.high.rate)],
    [`Non-high: ${rateLabel(kind).toLowerCase()}`, metric(a.non_high.rate), metric(b.non_high.rate)],
    [outs(kind) + ' (high)', int(a.high.outs), int(b.high.outs)],
    ['Adjusted pressure level', signed(a.estimates?.pressure), signed(b.estimates?.pressure)],
    ['Lift versus usual', signed(a.estimates?.lift), signed(b.estimates?.lift)],
    ['Conditional ordering score', signed(a.estimates?.score), signed(b.estimates?.score)],
    ['95% conditional interval', ...[a, b].map(p => p.estimates?.low == null ? 'Unavailable' :
      `${signed(p.estimates.low)} to ${signed(p.estimates.high)}`) as [string, string]],
  ];
  return <section className="sl-card sl-section">
    <span className="sl-kicker">Compare within a discipline</span>
    <h2>Player comparison</h2>
    <p>Use pressure balls and match counts to judge how much weight to put on each estimate.</p>
    <div className="sl-toggle">
      {kinds.map(k => <button key={k} aria-pressed={kind === k} onClick={() => { setKind(k); setIds(null); }}>{discipline[k]}</button>)}
    </div>
    <div className="sl-compare-selects">
      {[a, b].map((p, i) => <label key={i}>Player {i + 1}
        <select aria-label={`Player ${i + 1}`} value={p.id} onChange={e => setIds(i === 0 ? [Number(e.target.value), b.id] : [a.id, Number(e.target.value)])}>
          {choices.filter(option => option.id !== (i === 0 ? b.id : a.id)).map(option => <option key={option.id} value={option.id}>{option.name}</option>)}
        </select>
      </label>)}
    </div>
    <div className="sl-table-scroll"><table className="sl-detail-table"><thead><tr><th scope="col">Metric</th><th scope="col">{a.name}</th><th scope="col">{b.name}</th></tr></thead>
      <tbody>{cells.map(([label, x, y]) => <tr key={label}><th scope="row">{label}</th><td>{x}</td><td>{y}</td></tr>)}</tbody></table></div>
    <p className="sl-note">The adjusted estimates use run equivalents per six legal balls. Overlapping intervals are a reason to treat near ranks as uncertain.</p>
  </section>;
}

function Audit({ data, onPlayer }: { data: Snapshot; onPlayer: (row: Row, kind: Category) => void }) {
  const [kind, setKind] = useState<Category>('bat');
  const row = data.audit;
  return <div className="sl-audit">
    <section className="sl-card sl-section">
      <span className="sl-kicker">Verified inputs</span><h2>Data coverage</h2>
      <p>{int(row.accepted_legal_balls)} accepted legal deliveries, including {data.scoreboard_audit.verified_matches} games matched to Cricsheet. Recovered {int(data.scoreboard_audit.verified_extras_runs)} extras runs and restored {int(data.scoreboard_audit.restored_legal_balls)} legal balls. The selection pool contains 19 names after your exclusion.</p>
      <div className="sl-table-scroll"><table className="sl-detail-table"><thead><tr><th scope="col">Source file</th><th scope="col">Rows</th><th scope="col">Fields</th><th scope="col">Repeated keys</th></tr></thead><tbody>
        {Object.entries(row.source_files).map(([name, f]) => <tr key={name}><th scope="row">{name}</th><td>{int(f.rows)}</td><td>{f.columns}</td><td>{f.repeated_keys ?? 0}</td></tr>)}
      </tbody></table></div>
      <p className="sl-note">{int(row.excluded_extra_review.additional_dls_legal_balls_quarantined)} previously accepted legal balls flagged from D/L or DLS results. {int(row.excluded_extra_review.additional_ambiguous_legal_balls_quarantined)} more removed for unresolved endings. Team and XI coverage are checked without multiplying deliveries.</p>
    </section>
    <section className="sl-card sl-section">
      <span className="sl-kicker">Rating rules</span><h2>What pressure means here</h2>
      <div className="sl-method-grid">
        <div><h3>Batting under resource stress</h3><p>Before the ball: 2 wickets lost in overs 1–6; 3 down with a partnership below 30 off-bat runs in overs 7–10; 5 down in overs 11–15; 4 down in a chase from over 16; or 3 down in a knockout from over 11.</p></div>
        <div><h3>Bowling against established batting</h3><p>Before the ball: striker 20+ or partnership 35+ off-bat runs at the death; striker 30+ with at most 3 wickets down in overs 10–15; or striker 15+ or partnership 25+ from over 11 in a knockout.</p></div>
      </div>
      <p>The index weights adjusted pressure performance 75% and improvement over the player’s usual level 25%. Expectations compare phase, innings, role, competition family and year while excluding the player’s own deliveries. {data.method.bootstrap_draws} whole-match resamples quantify the variation in supported estimates. Evidence tiers describe sample strength; provisional entries follow supported candidates.</p>
      <p className="sl-note">Verified chases also use the exact runs required, balls remaining and wickets in hand. A contested chase has at most 36 balls remaining and a required rate between max(5, opening rate − 2.5) and min(18, opening rate + 4 − a low-wicket penalty). Batting also counts steep feasible chases in the last 60 balls. Unmatched games use the original observable triggers. Full bowling charges are shown only where verified.</p>
    </section>
    <section className="sl-card sl-section">
      <span className="sl-kicker">Sample and identity checks</span><h2>All 19 candidates</h2>
      <div className="sl-toggle">{kinds.map(k => <button key={k} aria-pressed={kind === k} onClick={() => setKind(k)}>{discipline[k]}</button>)}</div>
      <div className="sl-table-scroll"><table className="sl-detail-table">
        <thead><tr><th scope="col">Name and source</th><th scope="col">High balls</th><th scope="col">Evidence</th><th scope="col">Why</th></tr></thead>
        <tbody>{data.categories[kind].candidates.map(p => <tr key={p.id}>
          <th scope="row"><button className="sl-player" onClick={() => onPlayer(p, kind)}>{p.name}</button><small>{p.affiliation} · ID {p.id}</small></th>
          <td>{p.sample.high_balls}</td><td><TierBadge tier={p.tier} /></td><td>{p.reason}</td>
        </tr>)}</tbody>
      </table></div>
      <details className="sl-identities"><summary>Same-name records in the source</summary>
        {Object.entries(data.identities).filter(([, matches]) => matches.length > 1).map(([name, matches]) =>
          <div key={name}><strong>{name}</strong><ul>{matches.map(m => <li key={m.id}>ID {m.id} · {m.teams.join(', ')} · {m.used_for.length ? m.used_for.map(k => discipline[k]).join(' and ') : 'Separate source record; excluded'}</li>)}</ul></div>)}
      </details>
    </section>
    <section className="sl-card sl-section">
      <span className="sl-kicker">Model checks</span><h2>What changes the order?</h2>
      <p>Overlap counts repeat names from the main top ten. Open each scenario to see rank changes. Sensitivity does not give the probability of a future outcome.</p>
      <div className="sl-scenarios">{data.validation.sensitivity[kind].map(s => <details key={s.scenario}>
        <summary>{s.scenario}<span>{s.overlap}/{data.categories[kind].ranking.length} overlap · {s.ranked} ranked</span></summary>
        <p>{s.shifts.length ? s.shifts.map(m => `${m.player}: ${m.base} → ${m.scenario ?? 'out'}`).join(' · ') : 'No changes to selected ranks.'}</p>
      </details>)}</div>
      <h3>Chronological check · {discipline[kind]}</h3>
      <p>Spearman rank correlation with the next season’s adjusted high-pressure results. A dash means fewer than five comparable players or an undefined correlation.</p>
      <div className="sl-table-scroll"><table className="sl-detail-table">
        <thead><tr><th scope="col">Holdout</th><th scope="col">Scope</th><th scope="col">Players</th><th scope="col">Shortlist</th><th scope="col">Original pressure rules</th></tr></thead>
        <tbody>{data.validation.chronological[kind].map(f => <tr key={`${f.test_year}:${f.scope}`}>
          <td>{f.test_year}</td><th scope="row">{f.scope}</th><td>{f.common_players}</td><td>{metric(f.proposed, 3)}</td><td>{metric(f.legacy, 3)}</td>
        </tr>)}</tbody>
      </table></div>
      <p className="sl-note">The older v1 test used a different period and sample (ρ {metric(data.validation.legacy_holdout[kind].spearman, 3)}, n={data.validation.legacy_holdout[kind].common_players}); treat it as context. These retrospective checks do not establish IPL 2027 accuracy.</p>
    </section>
  </div>;
}

export default function ShortlistWorkspace() {
  const { data, isPending, error, refetch } = useQuery({ queryKey: ['screenshot-shortlist'], queryFn: load });
  const [tab, setTab] = useState<Section>('Rankings');
  const [search, setSearch] = useState('');
  const [profile, setProfile] = useState<{row: Row; kind: Category} | null>(null);
  const opener = useRef<HTMLElement | null>(null);
  const open = (row: Row, kind: Category) => {
    opener.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    setProfile({ row, kind });
  };
  const close = () => {
    setProfile(null);
    requestAnimationFrame(() => opener.current?.focus());
  };
  return <div className="sl-workspace sl-surface">
    <header className="sl-header"><div className="sl-header-in">
      <a href={offline ? '#' : '/'} className="sl-brand"><span className="sl-monogram">RR</span><span>SupeRR Selector<small>SEASON 2 · ROUND 1</small></span></a>
      <a className="rr-official" href="https://www.rajasthanroyals.com/" target="_blank" rel="noreferrer">Rajasthan Royals ↗</a>
    </div></header>
    <main className="sl-main">
      <RoyalsHero/>
      {isPending && <p className="sl-empty" role="status">Loading the local rankings…</p>}
      {error && <div className="sl-card sl-empty" role="alert">{error.message} <button className="sl-player" onClick={() => refetch()}>Retry</button></div>}
      {data && <>
        <div className="sl-summary">
          <div><span><ClipboardList size={15}/>Candidate pool</span><strong>{Object.keys(data.identities).length}</strong><small>Eligible screenshot names</small></div>
          <div><span><Database size={15}/>Legal deliveries</span><strong>{int(data.audit.accepted_legal_balls)}</strong><small>Through {data.source_cutoff} · scoreboard enhanced</small></div>
          <div><span><ShieldCheck size={15}/>Evidence coverage</span><strong>{data.scoreboard_audit.verified_matches} verified games</strong><small>Dhoni excluded at your request</small></div>
        </div>
        <nav className="sl-tabs" aria-label="Shortlist sections">
          {sections.map(({label, Icon}) => <button key={label} aria-pressed={tab === label} onClick={() => setTab(label)}><Icon size={16}/>{label}</button>)}
        </nav>
        {tab === 'Rankings' && <>
          <div className="sl-leaders">{kinds.map(kind => { const leader = data.categories[kind].ranking[0]; return leader && <button className="sl-leader" key={kind} onClick={() => open(leader, kind)}><span className="sl-kicker">01 / {discipline[kind]} leader</span><strong>{leader.name}</strong><span>{leader.role}</span><div><b>{signed(leader.estimates?.score)}</b> conservative score <i>↗</i></div><small>{leader.sample.high_balls} pressure balls · {leader.sample.high_matches} matches · {leader.tier}</small></button>; })}</div>
          <div className="sl-toolbar"><div><h2>Ranked selections</h2><p>Open any name for sample sizes, pressure metrics, and match evidence.</p></div>
            <label className="sl-search"><Search size={17}/><input type="search" value={search} onChange={e => setSearch(e.target.value)} placeholder="Search these rankings" aria-label="Search these rankings"/></label>
          </div>
          <div className="sl-rank-grid">{kinds.map(kind => <RankTable key={kind} side={data.categories[kind]} kind={kind} search={search.trim().toLowerCase()} onPlayer={open}/>)}</div>
          <div className="sl-reading"><ShieldCheck size={20}/><div><strong>How to read the tiers</strong><p>Substantial and supporting picks compete together on conservative pressure performance. Provisional picks fill open slots with thinner evidence. The rankings are historical; auction availability and bare dropdown identities require confirmation.</p></div>
            <button className="sl-player" onClick={() => setTab('Data & method')}>See the audit <ArrowRight size={15}/></button></div>
        </>}
        {tab === 'Compare' && <Comparison data={data}/>}
        {tab === 'Data & method' && <Audit data={data} onPlayer={open}/>}
        <section className="rr-gallery" aria-label="Rajasthan Royals photo gallery">
          <div><span className="sl-kicker">From the field</span><h2>ONE TEAM. ALL HEART.</h2><p>Your Rajasthan Royals photos.</p></div>
          <figure className="rr-wide"><img src={photo('celebration')} alt="Rajasthan Royals players celebrate together on the field" loading="lazy"/><figcaption>The moments we play for</figcaption></figure>
          <figure className="rr-small"><img src={photo('squad')} alt="Rajasthan Royals squad graphic" loading="lazy"/><figcaption>Royals together</figcaption></figure>
        </section>
        <footer className="sl-footer"><span>Independent SupeRR Selector analysis · RR pack + verified Cricsheet records</span><span>Snapshot {data.build_id} · {data.source_start} to {data.source_cutoff}</span></footer>
      </>}
      {profile && <PlayerDialog row={profile.row} kind={profile.kind} onClose={close} />}
    </main>
  </div>;
}
