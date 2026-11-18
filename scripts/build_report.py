"""Create the report and source-consistent player PDFs with bundled ReportLab."""
from pathlib import Path
import json
import html
import math
import shutil
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output'/'pdf';OUT.mkdir(parents=True,exist_ok=True)
DATA=json.loads((ROOT/'output'/'analysis.json').read_text(encoding='utf-8'))
INV=json.loads((ROOT/'output'/'dataset_inventory.json').read_text(encoding='utf-8'))
FONT=Path('C:/Windows/Fonts')
pdfmetrics.registerFont(TTFont('Segoe',str(FONT/'segoeui.ttf')))
pdfmetrics.registerFont(TTFont('Segoe-Bold',str(FONT/'segoeuib.ttf')))
pdfmetrics.registerFontFamily('Segoe',normal='Segoe',bold='Segoe-Bold',italic='Segoe',boldItalic='Segoe-Bold')
W,H=landscape(A4);M=40;CW=W-2*M
PURPLE=colors.HexColor('#302044');PINK=colors.HexColor('#cc377f');INK=colors.HexColor('#41334d');MUTED=colors.HexColor('#83728e');LINE=colors.HexColor('#e8e1ed');PALE=colors.HexColor('#f7f2fa')

def para(c,text,x,y,width,size=10,leading=None,color=INK,bold=False):
    style=ParagraphStyle('body',fontName='Segoe-Bold' if bold else 'Segoe',fontSize=size,leading=leading or size*1.5,textColor=color,spaceAfter=0,wordWrap='LTR')
    p=Paragraph(text,style);_,h=p.wrap(width,H);p.drawOn(c,x,y-h);return y-h

def esc(s):return html.escape(str(s))
def fmt(v,n=1):return 'n.a.' if v is None else f'{v:.{n}f}'

def table(c,rows,widths,x,y,size=8):
    rendered=[]
    for i,row in enumerate(rows):
        style=ParagraphStyle('cell',fontName='Segoe-Bold' if i==0 else 'Segoe',fontSize=size,leading=size*1.4,textColor=colors.white if i==0 else INK)
        rendered.append([Paragraph(str(s),style) for s in row])
    t=Table(rendered,colWidths=widths,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),PURPLE),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,PALE]),
                           ('LINEBELOW',(0,0),(-1,0),.6,PURPLE),('LINEBELOW',(0,1),(-1,-1),.3,LINE),
                           ('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),
                           ('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8)]))
    _,h=t.wrap(sum(widths),H);t.drawOn(c,x,y-h);return y-h

class Report:
    def __init__(self,path):
        self.c=canvas.Canvas(str(path),pagesize=(W,H));self.page=0;self.used=[]
        self.c.setTitle('SupeRR Selector Season 2 - Pressure Reliability and Auction Scouting')
        self.c.setAuthor('SupeRR Selector - Independent Analytics Submission')
    def new(self,kicker,title,subtitle=''):
        if self.page:self.c.showPage()
        self.page+=1;c=self.c
        c.setFillColor(colors.white);c.rect(0,0,W,H,fill=1,stroke=0)
        c.setFillColor(PINK);c.rect(M,H-37,24,2,fill=1,stroke=0)
        para(c,kicker.upper(),M,H-49,CW,8,12,MUTED,True)
        para(c,title,M,H-75,CW,25,31,PURPLE,True)
        if subtitle:para(c,subtitle,M,H-112,CW,9,14,MUTED)
        c.setStrokeColor(LINE);c.line(M,40,W-M,40)
        c.setFillColor(MUTED);c.setFont('Segoe',7)
        c.drawString(M,25,'SUPERR SELECTOR S2  /  RR SUPPLIED DATA  /  11 NOVEMBER 2026')
        c.drawRightString(W-M,25,f'{self.page:02d}')
        return H-145
    def finish(self,y):
        if y<52:raise ValueError(f'Page {self.page}: content below safe area ({y:.1f})')
        self.used.append((self.page,round(y,1)))
    def save(self):self.c.save()

def block(c,title,text,x,y,width,size=10):
    y=para(c,title,x,y,width,12,17,PURPLE,True)-8
    return para(c,text,x,y,width,size,size*1.5)-17

def profile_block(c,p,x,y,width,index=True):
    m=p['metrics'];kind=p['category']
    y=para(c,f"{p['rank']:02d}  {esc(p['name'])}",x,y,width,18,24,PURPLE,True)-5
    y=para(c,f"{esc(p['role'])}  |  {esc(', '.join(p['teams'][:3]))}",x,y,width,8.5,13,MUTED)-10
    stats=f"<b>{'BRS' if kind=='bat' else 'BoRS'} {p['score']:.2f}</b> / 100. Conditional 95% interval {fmt(p['score_low'])}-{fmt(p['score_high'])}. "
    stats+=f"High-pressure sample: <b>{m['high_balls']}</b> legal balls across {m['high_innings']} innings; {m['high_runs']} off-bat runs; {m['high_wickets']} {'striker dismissals' if kind=='bat' else 'credited wickets'}. "
    stats+=f"{'Runs per 100 legal balls' if kind=='bat' else 'Off-bat runs per 6 legal balls'}: high {m['high_rate']:.2f}, non-high {m['normal_rate']:.2f}. "
    stats+=f"Adjusted pressure impact {m['pressure_impact']:+.3f}; lift {m['pressure_lift']:+.3f}."
    y=para(c,stats,x,y,width,9,13.5)-10
    y=para(c,f"<b>Potential RR role:</b> {esc(p['fit'])}",x,y,width,9,13.5)-7
    y=para(c,f"<b>Risk:</b> {esc(p['risk'])}",x,y,width,9,13.5)-7
    y=para(c,f"<b>Recommendation:</b> {esc(p['recommendation'])}. {esc(p['availability'])}.",x,y,width,9,13.5)-7
    if p['public_research']:
        s=p['public_research'][0]
        y=para(c,f"<b>Public context:</b> {esc(s['note'])}",x,y,width,8.5,12.5,MUTED)-7
    example=sorted(p['pressure_matches'],key=lambda q:q['balls'],reverse=True)[0]
    y=para(c,f"<b>Audit example:</b> match {example['match_id']}, innings {example['innings']}, {example['date']}, {esc(example['competition'])}. {example['balls']} high-pressure legal balls. Source CSV rows {', '.join(str(v) for v in example['source_rows'][:6])}{' ...' if len(example['source_rows'])>6 else ''}.",x,y,width,8,12,MUTED)-7
    y=para(c,f"Top-10 membership in weight scenarios: {p['stability']['top10_weight_frequency']:.1f}%. This measures weight sensitivity only. Source coverage: {esc(', '.join(p['families']))}; years {', '.join(map(str,p['seasons']))}.",x,y,width,8,12,MUTED)
    return y

def intervals(c,players,x,y,width,height,title):
    para(c,title,x,y,width,12,17,PURPLE,True)
    labelw=132;plotx=x+labelw;plotw=width-labelw-15;top=y-36;rowh=(height-60)/10
    for tick in [0,25,50,75,100]:
        xx=plotx+plotw*tick/100;c.setStrokeColor(LINE);c.setLineWidth(.5);c.line(xx,top+3,xx,top-10*rowh+12)
        c.setFillColor(MUTED);c.setFont('Segoe',7);c.drawCentredString(xx,top-10*rowh-5,str(tick))
    for i,p in enumerate(players):
        yy=top-i*rowh
        para(c,p['name'],x,yy+6,labelw-8,8,11)
        lo=p['score_low'] or 0;hi=p['score_high'] or 0
        c.setStrokeColor(colors.HexColor('#ddc4df'));c.setLineWidth(5);c.line(plotx+lo/100*plotw,yy,plotx+hi/100*plotw,yy)
        c.setFillColor(PINK);c.circle(plotx+p['score']/100*plotw,yy,3,fill=1,stroke=0)
    return top-10*rowh-25

def main():
    report=Report(OUT/'SupeRR_Selector_Report.pdf');c=report.c;d=DATA;o=d['overview'];method=d['methodology']
    # Cover is intentionally the only full-bleed page.
    report.page=1;c.setFillColor(PURPLE);c.rect(0,0,W,H,fill=1,stroke=0)
    c.setFillColor(PINK);c.rect(50,H-73,40,4,fill=1,stroke=0)
    para(c,'SUPERR SELECTOR  /  SEASON 2  /  ROUND 1',50,H-95,CW,10,15,colors.HexColor('#e4b2d2'),True)
    para(c,'Reliability when<br/>the game gets difficult.',50,H-160,650,43,54,colors.white,True)
    para(c,'Rajasthan Royals IPL 2027<br/>Pressure analytics and auction scouting report',53,H-300,600,19,28,colors.HexColor('#d7c4e3'))
    para(c,'Two ordered top-10 lists. Observable match context.<br/>Measured uncertainty. A reproducible analysis.',53,155,600,12,20,colors.HexColor('#c7afd8'))
    para(c,'11 NOVEMBER 2026   |   SOURCE DATA: 22 JAN 2022 - 01 NOV 2026',53,56,CW,8,12,colors.HexColor('#b497c9'))
    c.setStrokeColor(colors.HexColor('#755181'));c.setLineWidth(1);c.circle(748,340,160);c.circle(748,340,123);c.circle(748,340,86)
    c.setFillColor(PINK);c.circle(748,340,40,fill=1,stroke=0)
    report.used.append((1,56))
    y=report.new('01 / Executive summary','Rank players from the evidence, then verify the decision.','The model describes reliability in the supplied sample. It does not establish future performance or auction availability.')
    stats=[(f"{o['players_observed']:,}",'players observed'),(f"{o['source_matches']:,}",'matches audited'),(f"{o['legal_model_deliveries']:,}",'legal model deliveries'),(str(o['ranked_batters']+o['ranked_bowlers']),'eligible category ratings')]
    for i,(value,label) in enumerate(stats):
        xx=M+i*CW/4;c.setFillColor(PALE);c.roundRect(xx,y-68,CW/4-12,68,6,fill=1,stroke=0)
        para(c,value,xx+13,y-10,CW/4-30,23,28,PURPLE,True);para(c,label,xx+13,y-43,CW/4-30,8,12,MUTED)
    y-=93
    a,b=d['rankings']['bat'][0],d['rankings']['bowl'][0]
    y=block(c,'Leading batter: '+a['name'],f"BRS {a['score']:.2f}; {a['metrics']['high_balls']} high-pressure legal balls. Recorded scoring rate {a['metrics']['high_rate']:.2f} runs / 100 legal balls; adjusted pressure impact {a['metrics']['pressure_impact']:+.3f} runs per ball.",M,y,CW)
    y=block(c,'Leading bowler: '+b['name'],f"BoRS {b['score']:.2f}; {b['metrics']['high_balls']} high-pressure legal balls and {b['metrics']['high_wickets']} credited wickets. Conditional interval {fmt(b['score_low'])}-{fmt(b['score_high'])} remains wide, so this is a scouting lead rather than a certainty.",M,y,CW)
    y=block(c,'Decision-critical limitations','Missing extras amounts prevent complete scoreboard pressure and full economy. Batting top-10 overlap is only 5/10 under both looser and stricter pressure rules. The batting chronological holdout correlation is negative. The report exposes these findings instead of claiming predictive accuracy.',M,y,CW)
    report.finish(y)
    y=report.new('02 / Dataset audit','All supplied sources inspected. Originals preserved.','No Excel workbooks were supplied. Row counts refer to CSV data rows, excluding headers.')
    rows=[['Source','Rows','Fields','Role in analysis']]
    uses={'ball_by_ball.csv':'Delivery outcomes, identities and observable pre-ball context','matches.csv':'Date, competition, knockout and revision flags','competitions.csv':'Format, season and competition identity','teams.csv':'Team display names by competition','playing_eleven.csv':'Roster cross-checks and available keeper/captain flags','competition_team_player_mapping.csv':'Canonical IDs, source display names and roster relationships'}
    for f in INV['files']:
        if 'rows' in f:rows.append([Path(f['file']).name,f"{f['rows']:,}",str(f['columns']),uses[Path(f['file']).name]])
    y=table(c,rows,[231,60,50,CW-341],M,y,8.5)-18
    y=block(c,'Integrity and joins','No exact duplicate delivery rows and no duplicate match/innings/delivery-event keys. No delivery match or match competition orphans. Sixteen match metadata records have no ball data. Names are display strings; IDs carry identity. Source SHA-256 hashes, every column, data types, missing counts and examples are in dataset_inventory.json and data_dictionary.md.',M,y,CW)
    y=para(c,f"Retained {o['valid_innings']:,} innings from {o['valid_matches']} matches, with {o['legal_model_deliveries']:,} legal deliveries. Quarantine counts overlap: {o['exclusions_overlapping']['ambiguous_extra_innings']} innings with ambiguous extras, {o['exclusions_overlapping']['sequence_inconsistent_innings']} with inconsistent sequences, {o['exclusions_overlapping']['revised_match_innings']} revised-match innings, {o['exclusions_overlapping']['unfinished_match_innings']} unfinished-match innings and {o['exclusions_overlapping']['super_over_innings']} super-over innings.",M,y,CW,9,14)
    report.finish(y)
    y=report.new('03 / Data semantics','The most important discovery is a data constraint.','A plausible column label is not enough to justify a cricket statistic.')
    rows=[['Field or issue','Observed evidence','Analytical treatment'],['extras1_runs','189,167 no-extra rows all carry 6; wide rows carry 2, legbyes 3, Overstep 1. It is a category code.','Never sum as runs. Do not replace missing extras with assumed values.'],['runs / extras_2_runs','runs contains off-bat scoring. Secondary extras are sparse and do not recover primary values.','No exact running score, universal target/RRR or full bowling economy is claimed.'],['over / delivery counters','overid is 1-based. Event counters include illegal deliveries.','Known wide and Overstep events excluded from legal-ball metrics. Entire innings with ambiguous events or inconsistent complete-over counts quarantined.'],['Wickets','Actual dismissed_player_id can differ from striker_id. RunOut is not a bowler wicket.','Batting quality uses legal-ball striker dismissals only. Bowling credit: Caught, Bowled, LBW, Stump and Hit Wicket.'],['Boundary / speed flags','23 boundary/runs flag mismatches; 77,862 nonpositive recorded speeds.','Boundary percentage uses explicit boundary flags. Speed is excluded. No automatic value repair.'],['Revised-overs labels','Non-null values range from 30 to 114, consistent with a ball allocation rather than literal overs.','All revised matches excluded from primary scoring. No inference needed about exact revised timing.']]
    y=table(c,rows,[132,283,CW-415],M,y,9)-15
    y=para(c,'Reported scoring rates are runs per 100 legal balls. Bowling rates are off-bat runs per six legal deliveries. Neither is labelled as an official career strike rate or full economy. A zero off-bat delivery may still concede extras.',M,y,CW,9,14,PINK)
    report.finish(y)
    y=report.new('04 / Pressure classification','Different roles face different kinds of pressure.','All signals are evaluated before the current delivery. Neither the eventual winner nor the final margin labels pressure.')
    col=(CW-30)/2;yb=y;yw=y
    yb=para(c,'BATTING: RESOURCE STRESS',M,yb,col,12,18,PURPLE,True)-12
    for i,rule in enumerate(method['bat_rules']):yb=para(c,f"<b>{i+1}.</b> {esc(rule)}.",M,yb,col,10,15)-10
    yw=para(c,'BOWLING: ESTABLISHED RESISTANCE',M+col+30,yw,col,12,18,PURPLE,True)-12
    for i,rule in enumerate(method['bowl_rules']):yw=para(c,f"<b>{i+1}.</b> {esc(rule)}.",M+col+30,yw,col,10,15)-10
    y=min(yb,yw)-8
    y=block(c,'Moderate and normal labels',esc(method['moderate_rules']),M,y,CW)
    y=para(c,f"Classification produces {o['high_batting_balls']:,} batting and {o['high_bowling_balls']:,} bowling high-pressure legal balls. Counts overlap; do not add them as unique situations. The batting framework mainly detects collapse/rebuild stress; it cannot identify every difficult chase or finisher situation without trustworthy team score.",M,y,CW,9,14)
    report.finish(y)
    y=report.new('05 / Reliability models','Context first. Shrink small samples. Explain every component.','Initial weights are analyst hypotheses, not fitted or validated optimal coefficients.')
    y=para(c,'Reliability = (35P + 20C + 15A/W + 15E/R + 5S) / 90',M,y,CW,18,26,PURPLE,True)-15
    rows=[['Component','Effective weight','Definition'],['P: pressure','38.89%','65% percentile of shrunken high-pressure quality; 35% percentile of pressure-minus-non-high lift.'],['C: consistency','22.22%','Equal percentiles of smoothed pressure-innings success frequency and inverse variability. At least 3 pressure balls define an effective consistency innings; Beta(4,4) and an 8-innings variance prior.'],['A / W','16.67%','Batter: mean context quality across observed phases with at least 24 balls. Bowler: context-adjusted credited wicket-rate percentile. Unobserved phases do not receive zeros.'],['E / R','16.67%','Batter: equal scoring and survival residual percentiles. Bowler: off-bat run-suppression percentile.'],['S: sample support','5.56%','100 x sqrt[(high balls / (high balls+120)) x (effective pressure innings / (effective pressure innings+10))].'],['Match impact','Omitted','A full scoreboard and calibrated win-probability model are unavailable. Original 10% removed; remaining weights renormalised. No team-win credit assigned.']]
    y=table(c,rows,[115,86,CW-201],M,y,8.5)-14
    y=para(c,'Context baseline: family x year x phase x innings x batting-position group or bowling family, with a 240-ball prior toward phase/innings/role peers. Quality trades a striker dismissal or credited wicket at an assumed 12 runs; tested at 8 and 16. High and non-high mean qualities shrink toward zero using 120-ball priors. Components use tied midrank percentiles across the eligible category.',M,y,CW,9,14)
    report.finish(y)
    for kind,caption in [('bat','Batters'),('bowl','Bowlers')]:
        y=report.new('06 / Final ordered rankings' if kind=='bat' else '07 / Final ordered rankings',f'{caption}: top 10 in the base model.','Use these source display names and rank order in Unstop. Rankings are descriptive and independent across disciplines.')
        rows=[['#','Source player name','Score','95% interval','High balls','High runs','High outs' if kind=='bat' else 'High W','Rate*','P','C','A' if kind=='bat' else 'W','E' if kind=='bat' else 'R','S']]
        for p in d['rankings'][kind][:10]:
            m=p['metrics'];co=p['components']
            rows.append([p['rank'],p['name'],fmt(p['score']),f"{fmt(p['score_low'])}-{fmt(p['score_high'])}",m['high_balls'],m['high_runs'],m['high_wickets'],fmt(m['high_rate'],2)]+[fmt(co[k]) for k in ['pressure','consistency','adaptability','efficiency','confidence']])
        widths=[24,160,42,74,52,52,50,55,50,50,50,50,0]
        # Sum widths exactly; minimum readable S width.
        widths[-1]=CW-sum(widths[:-1])
        y=table(c,rows,widths,M,y,7.5)-16
        y=para(c,('* Rate: recorded runs per 100 legal balls. Outs are legal-ball striker dismissals.' if kind=='bat' else '* Rate: off-bat runs conceded per 6 legal deliveries, not economy. W includes credited dismissals only.')+' P/C/A(W)/E(R)/S are 0-100 component scores. Match impact is unavailable. Intervals hold the cohort and normalization fixed.',M,y,CW,9,14,MUTED)-12
        y=para(c,'Eligibility: '+('300 legal balls, 80 pressure balls, 15 innings and 8 pressure innings.' if kind=='bat' else '360 legal balls, 100 pressure balls, 15 innings and 10 pressure innings.')+' At least one valid source appearance in 2025 or 2026. Pressure innings in the eligibility gate need at least one high-pressure ball; consistency uses at least three.',M,y,CW,9,14)
        report.finish(y)
    y=report.new('08 / Comparison','Exact ranks are less certain than a single number suggests.','Dots: point score. Bands: conditional 95% intervals from 300 within-player innings-cluster bootstrap draws.')
    col=(CW-25)/2
    y1=intervals(c,d['rankings']['bat'][:10],M,y,col,310,'Batters')
    y2=intervals(c,d['rankings']['bowl'][:10],M+col+25,y,col,310,'Bowlers')
    y=min(y1,y2)-12
    y=para(c,'Resample complete innings within each player so phase and pressure observations stay together. Recalculate components while keeping eligibility, context expectations and eligible-peer normalization fixed. These intervals exclude source measurement error, selection of the pressure framework and changes in the eligible peer cohort. Wide overlaps mean adjacent places should not be treated as definitive.',M,y,CW,9,14)
    report.finish(y)
    y=report.new('09 / Validation','Show the checks that challenge the result.','Pre-specified base assumptions are retained; no retuning on the holdout to improve the displayed association.')
    rows=[['Validation','Batting','Bowling','Reading']]
    for i,t in enumerate(d['validation']['bat']['threshold_tests']):rows.append([t['scenario'],f"{t['top10_overlap']}/10",f"{d['validation']['bowl']['threshold_tests'][i]['top10_overlap']}/10",'Base top-10 membership overlap; order can also change.'])
    rows += [['IPL-only ranking','8/10','6/10','Competition mix matters; league context normalization does not prove transferability.'],['25% higher opportunity gates','8/10','8/10','Smaller samples affect selection; especially important for Rasikh Salam and Mark Adair.'],['Chronological holdout Spearman',fmt(d['validation']['bat']['chronological_holdout']['spearman'],3),fmt(d['validation']['bowl']['chronological_holdout']['spearman'],3),'2022-24 score versus 2025-26 high-pressure impact. Expectations fitted on training data only.'],['Holdout common players','35','31','Requires at least 50 holdout pressure balls. Small samples limit inference.']]
    y=table(c,rows,[185,70,70,CW-325],M,y,8.5)-16
    y=para(c,'<b>The batting holdout does not support a positive future-performance claim.</b> The positive bowling association is exploratory, not causal or an established forecast. Weights are also varied across 400 Dirichlet scenarios (concentration 200); individual top-10 frequencies are shown in profiles. Weight stability does not imply pressure-definition stability.',M,y,CW,10,15,PINK)
    report.finish(y)
    for kind,label in [('bat','Batter scouting'),('bowl','Bowler scouting')]:
        for i in range(0,10,2):
            y=report.new('10 / Player dossiers',f'{label}: ranks {i+1} and {i+2}.','Proprietary measurements and public supporting context are explicitly separated. No price estimates are assigned.')
            col=(CW-34)/2
            y1=profile_block(c,d['rankings'][kind][i],M,y,col)
            y2=profile_block(c,d['rankings'][kind][i+1],M+col+34,y,col)
            report.finish(min(y1,y2))
    y=report.new('11 / Alternative candidates','A ranking should also explain who falls just outside.','The candidates below retain their computed rank. No discretionary reorder is applied.')
    for kind,label in [('bat','Batting alternatives'),('bowl','Bowling alternatives')]:
        y=para(c,label,M,y,CW,12,17,PURPLE,True)-10
        rows=[['Rank','Player','Score','Pressure balls','Lowest measured component / why below selection']]
        labels={'pressure':'Pressure','consistency':'Consistency','adaptability':'Adaptability' if kind=='bat' else 'Wicket taking','efficiency':'Efficiency' if kind=='bat' else 'Run control','confidence':'Sample support'}
        for p in d['rankings'][kind][10:14]:
            key=min(labels,key=lambda k:p['components'][k])
            rows.append([p['rank'],p['name'],fmt(p['score']),p['metrics']['high_balls'],f"{labels[key]} {p['components'][key]:.1f}. Lower weighted total than the base top-10 boundary; other scenarios can change membership."])
        y=table(c,rows,[34,155,48,70,CW-307],M,y,8)-17
    report.finish(y)
    y=report.new('12 / RR squad fit','Scouting priorities are conditional, not assumed vacancies.','The official submission asks for 10 batters and 10 bowlers. A separate 10-player overall list is unnecessary.')
    y=block(c,'Map evidence to roles','Batting: evaluate middle-order rebuild options such as Rinku Singh, Tristan Stubbs, Shashank Singh and Tilak Varma. Distinguish those innings from top-order scoring options such as Jos Buttler. Bowling: compare established-batter resistance, pace/spin balance and phase exposure before choosing a role. The legal-ball metric cannot substitute for full death-over economy.',M,y,CW,9)
    y=block(c,'Do not infer the auction market','RR reported buying Ravi Bishnoi and Adam Milne while completing its 2026 squad on 16 December 2025. This is a dated squad reference, not the 2027 roster, purse or vacancy list. Final 2027 retention, registration, injury, release and purse information must be checked before turning a player ranking into a bid plan.',M,y,CW,9)
    y=block(c,'Material player constraints','Khaleel Ahmed: IPL confirmed his SRH trade on 5 November 2026; do not assume auction availability. Hasaranga: the 10 April 2026 injury-replacement advisory requires a new fitness check. Nawaz: T20I performance does not establish IPL eligibility. Dhoni: historical reliability does not establish future participation.',M,y,CW,9)
    y=para(c,'Rasikh Salam and Shashank Singh warrant video and full-scorecard review. No claim of market undervaluation is made: prices, registration and reputation benchmarks were not supplied.',M,y,CW,9,14)
    report.finish(y)
    y=report.new('13 / Reproduction and submission','One computation supplies the report, API and dashboard.','No hand-entered final ranking overrides or fabricated statistics are used.')
    y=block(c,'Reproduction recipe','1. Run python scripts/inventory.py. 2. Run python -m backend.analytics.pipeline --bootstrap 300. 3. Run python scripts/enrich_research.py. 4. Use the bundled PDF Python runtime to run scripts/build_report.py. 5. Run the analytics/API checks and npm run build. The fixed bootstrap seed is 202711. Source file hashes identify the input pack.',M,y,CW)
    y=block(c,'Traceability','analysis.json is the shared computed snapshot. bat_rankings.csv and bowl_rankings.csv retain every eligible score and component. delivery_evidence.csv.gz stores source physical row numbers, pre-ball state, labels and expected/contributed values. dataset_inventory.json and data_dictionary.md cover every supplied CSV column. Public sources never change score values.',M,y,CW)
    y=block(c,'Form entries','Select the two top-10 lists exactly as printed. The screenshot verifies the full spelling Mahendra Singh Dhoni. Other chosen names preserve source roster strings but have not all been verified in the live Unstop dropdown. Upload this PDF. Use only the final verified deployment URL for the optional dashboard field.',M,y,CW)
    y=block(c,'Optional journey content','The form asks for a link to a reel, post or short video, not a prose essay. A 45-second sequence can show the audit, explain pressure rules, compare one batting and bowling profile, and end with the uncertainty and RR scouting use. A caption and storyboard are supplied separately. No social post or journey URL has been fabricated.',M,y,CW)
    report.finish(y)
    sources=d['research']
    for start in range(0,len(sources),8):
        y=report.new('14 / Public references',f'Supporting sources {start+1}-{min(start+8,len(sources))}.','Checked 11 November 2026. Source notes describe only verified context; no full career or domestic completeness is claimed.')
        col=(CW-30)/2
        bottoms=[]
        for ci in range(2):
            yy=y
            for j,s in enumerate(sources[start+ci*4:start+ci*4+4]):
                n=start+ci*4+j+1
                yy=para(c,f"<b>{n:02d}. {esc(s['title'])}</b>",M+ci*(col+30),yy,col,9,13,PURPLE)-4
                yy=para(c,f"<link href='{esc(s['url'])}' color='#a34a88'>{esc(s['url'])}</link>",M+ci*(col+30),yy,col,7,10)-4
                yy=para(c,esc(s['note']),M+ci*(col+30),yy,col,8,12,MUTED)-15
            bottoms.append(yy)
        report.finish(min(bottoms))
    report.save()
    # Individual player PDFs are a convenience export, generated from the same snapshot.
    individual=OUT/'players';individual.mkdir(exist_ok=True)
    for kind in ['bat','bowl']:
        for p in d['rankings'][kind]:
            rp=Report(individual/f"{kind}-{p['id']}.pdf")
            y=rp.new('Scouting profile',p['name'],'Source: RR supplied pack, legal-delivery subset. Statistical ranking does not verify auction availability.')
            y=profile_block(rp.c,p,M,y,CW)
            rp.finish(y);rp.save()
    shutil.copy2(OUT/'SupeRR_Selector_Report.pdf',ROOT/'frontend'/'public'/'SupeRR_Selector_Report.pdf')
    (ROOT/'output'/'pdf_layout_checks.json').write_text(json.dumps({'pages':report.page,'content_bottom_points':report.used},indent=2),encoding='utf-8')
    # Standalone methodology: use exact machine-readable model descriptions.
    lines=['# SupeRR Selector methodology', '', 'Version 1.0.0; source cutoff 1 November 2026; prepared 11 November 2026.', '']
    for key,value in method.items():
        lines.extend(['## '+key.replace('_',' ').capitalize(),''])
        if isinstance(value,(dict,list)):lines.extend(['```json',json.dumps(value,indent=2),'```',''])
        else:lines.extend([str(value),''])
    (ROOT/'output'/'Methodology.md').write_text('\n'.join(lines),encoding='utf-8')
    print(f'Created {report.page}-page report and {len(d["rankings"]["bat"])+len(d["rankings"]["bowl"])} player PDFs.')

if __name__=='__main__':main()
