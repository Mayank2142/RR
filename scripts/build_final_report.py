"""Render the final scoreboard-enhanced shortlist with explicit exclusions."""
from html import escape
import json
from pathlib import Path
import shutil
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output/pdf/SupeRR_Screenshot_Shortlist_Report.pdf'
WIDTH = A4[0]-80


def main():
    d=json.loads((ROOT/'output/shortlist/shortlist.json').read_text(encoding='utf-8'))
    pink, navy, grey = map(colors.HexColor, ['#da0878','#17285d','#5c6173'])
    fonts=Path('C:/Windows/Fonts')
    pdfmetrics.registerFont(TTFont('RR',str(fonts/'segoeui.ttf')))
    pdfmetrics.registerFont(TTFont('RRBold',str(fonts/'segoeuib.ttf')))
    pdfmetrics.registerFontFamily('RR',normal='RR',bold='RRBold')
    styles={
        'body': ParagraphStyle('body',fontName='RR',fontSize=10,leading=15,textColor=navy,spaceAfter=10),
        'title': ParagraphStyle('title',fontName='RRBold',fontSize=28,leading=33,textColor=navy,spaceAfter=18),
        'heading': ParagraphStyle('heading',fontName='RRBold',fontSize=16,leading=21,textColor=pink,spaceAfter=10),
        'small': ParagraphStyle('small',fontName='RR',fontSize=8,leading=11,textColor=grey,spaceAfter=8)}
    story=[]
    def text(value, style='body'):
        story.append(Paragraph(value,styles[style]))
    def page(title):
        story.append(PageBreak())
        text(title,'title')
    def photo(name,w,h):
        return Image(str(ROOT/f'frontend/public/rr/{name}.png'),width=w,height=h,kind='proportional')
    def table(rows,widths):
        t=Table([[Paragraph(str(v),styles['small']) for v in row] for row in rows],colWidths=widths,repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#f8d9eb')),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f3f4f9')]),
            ('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),7),
            ('BOTTOMPADDING',(0,0),(-1,-1),6),('LINEBELOW',(0,0),(-1,0),1,pink)]))
        story.extend([t,Spacer(1,14)])
    def number(v):
        return 'Unavailable' if v is None else f'{v:+.2f}'

    text('SUPERR SELECTOR / SEASON 2 / ROUND 1','small')
    text('Pressure players.<br/>The final shortlist.','title')
    text('Rajasthan Royals scouting analysis','heading')
    story.extend([photo('team',WIDTH,260),Spacer(1,18)])
    text('19 eligible names from your screenshots. Mahendra Singh Dhoni excluded at your request. Two ordered lists use the supplied data and verified public delivery records.')
    a=d['scoreboard_audit']
    text(f"{a['scored_legal_balls']:,} legal deliveries assessed. {a['verified_matches']} matched public games. Data through 1 November 2026. Prepared 18 November 2026.")
    text('Independent competition analysis. Team photographs supplied by the user. Visual reference https://www.rajasthanroyals.com/','small')
    page('Your two ordered lists')
    rows=[['Rank','Batter','Bowler']]
    for b,w in zip(d['categories']['bat']['ranking'],d['categories']['bowl']['ranking']):
        rows.append([b['rank'],escape(b['name']),escape(w['name'])+(' *' if w['tier']=='Provisional' else '')])
    table(rows,[35,240,WIDTH-275])
    text('* Provisional bowling picks have fewer than four pressure matches. Pradeep Sangwan has only two high-pressure legal deliveries across two matches.')
    text('Confirm player identities','heading')
    text('Haider Ali is Pakistan player ID 7338 for batting and UAE player ID 28756 for bowling. Rashid Khan is Afghanistan player ID 4722. Abdul Samad is the IPL batter, ID 7446. Confirm the player behind ambiguous dropdown labels.')
    text('Rohit Sharma takes the open batting position after the exclusion. Peer expectations use all validated players in the wider data pack.')
    page('How the rating works')
    text('Pre-delivery pressure','heading')
    text('Original batting triggers measure early collapse, depleted wickets, late chases short on wickets and knockout rebuilds. Bowling triggers measure established strikers and partnerships, especially at the death and in knockouts.')
    text('Verified chase scoreboard','heading')
    text('A contested finish has at most 36 balls remaining. Required rate lies between max(5, opening rate - 2.5) and min(18, opening rate + 4 - 1.5 x max(0, 3 - wickets in hand)). Opening rate equals target / 20. Batting also counts feasible steep chases with at most 60 balls remaining and rate at least max(9, opening rate + 1.5). These bounds are analyst assumptions. Only information available before the delivery enters the label.')
    text('Context adjustment','heading')
    text('Compare off-bat runs and wickets with phase, innings, role, competition and year peers, excluding the player. Batting residual adds scoring above expectation and subtracts 12 times excess striker dismissals. Bowling adds run suppression and 12 times excess credited wickets. A 12-run wicket value is an explicit assumption.')
    text('Conservative ordering','heading')
    text('U = non-high residual sum / (non-high balls + 120). P = (high residual sum + 60 x U) / (high balls + 60). Point estimate = 6 x [0.75 x P + 0.25 x (P - U)]. Supported players rank by the 20th percentile of 800 whole-match resamples. The 95% intervals hold peer expectations and pressure rules fixed.')
    text('Substantial batting gates are 300 total / 80 high balls / 15 innings / 8 high innings. Supporting gates are 100 / 25 / 5 / 4. Bowling gates are 360 / 100 / 15 / 10 and 72 / 18 / 4 / 4. Both supported tiers require four high-pressure matches. Provisional order uses high matches, then high balls, then the point estimate.')
    page('Verified data and coverage')
    table([['Measure','Result'],['Public matches',a['verified_matches']],['IPL',a['verified_by_family']['IPL']],
           ['T20I',a['verified_by_family']['T20I']],['Events matched',f"{a['verified_events']:,}"],
           ['Extras runs recovered',f"{a['verified_extras_runs']:,}"],['Legal balls restored',f"{a['restored_legal_balls']:,}"],
           ['All scored legal balls',f"{a['scored_legal_balls']:,}"]],[WIDTH*.65,WIDTH*.35])
    text('Match linkage checks dates, teams, delivery counts, over numbers, off-bat runs, extras categories, wickets, player identities, targets, allocations and final score margins. The crosswalk preserves accepted and rejected links. Revised, incomplete or conflicting matches remain outside scoreboard recovery.')
    text('Unmatched games retain validated proxy context. Main model outcomes use legal balls and off-bat runs for comparability. Verified bowling economy including wide/no-ball charges is retained separately. Public source totals therefore improve pressure classification and event coverage.')
    text('Sources','heading')
    text('Six original RR CSVs with SHA256 checks. Public data https://cricsheet.org/downloads/ipl_json.zip and https://cricsheet.org/downloads/t20s_male_json.zip. Schema https://cricsheet.org/format/json/. Archive hashes, match crosswalk and source rows accompany the local results.','small')
    for kind in ('bat','bowl'):
        players=d['categories'][kind]['ranking']
        for start in range(0,10,2):
            page(('Batting' if kind=='bat' else 'Bowling')+f' evidence / {start+1}-{start+2}')
            for p in players[start:start+2]:
                s,e,h,n=p['sample'],p['estimates'],p['high'],p['non_high']
                text(f"{p['rank']:02d} &nbsp; {escape(p['name'])}",'heading')
                text(f"{escape(p['affiliation'])} / ID {p['id']}<br/>{escape(p['role'])} / {p['tier']} / last observed {s['last_seen']}",'small')
                table([['Metric','High','Non-high'],['Legal balls',h['balls'],n['balls']],['Off-bat runs',h['runs'],n['runs']],
                       ['Striker dismissals' if kind=='bat' else 'Credited wickets',h['outs'],n['outs']],
                       ['Runs / 100 legal balls' if kind=='bat' else 'Off-bat runs / six legal balls',h['rate'],n['rate']]], [WIDTH*.54,WIDTH*.23,WIDTH*.23])
                text(f"Conservative score {number(e['score'])}. Lift {number(e['lift'])}. 95% interval {number(e['low'])} to {number(e['high'])}. {s['high_matches']} pressure matches.")
                text(escape(p['rr_note']))
                x=p['examples'][0]
                text(f"Evidence example {escape(x['competition'])}, {x['date']}. Match {x['match_id']}, innings {x['innings']}. Original rows {', '.join(map(str,x['source_rows']))}.",'small')
                story.append(Spacer(1,12))
    page('Validation and decision limits')
    rows=[['Discipline / year','Players','Scoreboard','Original rules']]
    for k in ('bat','bowl'):
        for f in d['validation']['chronological'][k]:
            if f['scope']=='All covered players':
                rows.append([k+' / '+str(f['test_year']),f['common_players'],number(f['proposed']),number(f['legacy'])])
    table(rows,[175,60,135,WIDTH-370])
    text('Values are Spearman correlations with later verified chase performance. Peer expectations train on earlier games. Forecasting gains remain inconsistent. These retrospective checks use years previously examined during model development. Historical evaluation cohorts include all originally eligible candidates before the requested exclusion.')
    text('Player registration, retirement, retention, fitness and auction prices require additional verification. Bowling ranks 8-10 have provisional evidence. The two Haider Ali identities need confirmation in the form.')
    text('Photographs supplied by you','heading')
    images=Table([[photo('celebration',WIDTH*.5,115),photo('squad',WIDTH*.18,115),photo('royals-palace',WIDTH*.18,115)]],colWidths=[WIDTH*.56,WIDTH*.22,WIDTH*.22])
    story.append(images)
    text('The dashboard, PDF and form CSV reproduce the same snapshot.','small')
    def footer(canvas,document):
        canvas.setStrokeColor(pink)
        canvas.line(40,39,A4[0]-40,39)
        canvas.setFont('RR',7)
        canvas.setFillColor(grey)
        canvas.drawString(40,25,'SUPERR SELECTOR / '+d['build_id'])
        canvas.drawRightString(A4[0]-40,25,str(document.page))
    pending=OUT.with_suffix('.pdf.tmp')
    SimpleDocTemplate(str(pending),pagesize=A4,rightMargin=40,leftMargin=40,topMargin=40,bottomMargin=55,
                      title='SupeRR Selector - Final shortlist',author='Independent scouting analysis').build(story,onFirstPage=footer,onLaterPages=footer)
    pending.replace(OUT)
    shutil.copyfile(OUT,ROOT/'frontend/public'/OUT.name)
    print(OUT)


if __name__ == '__main__':
    main()
