"""Public-source research register. Human-reviewed summaries; never modifies scores."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
DATE='2026-11-11'
# Each tuple was verified through web search/open on the date above. No unvisited URLs.
RESEARCH={
 'Rinku Singh':('KKR official player profile','https://www.kkr.in/players/rinku-singh-profile-64727','KKR describes his lower-middle-order finishing role. Profile includes an IPL statistics panel; its biography contains older season text, so career narrative is not treated as current-form proof.'),
 'Mahendra Singh Dhoni':('IPL official MS Dhoni profile','https://www.iplt20.com/teams/royal-challengers-banglore/squad-details/1','Page identifies MS Dhoni as a wicketkeeper batter, born 7 July 1981, and discusses CSK. The URL team segment is inconsistent with the page title. Historical reliability does not establish 2027 availability.'),
 'Tristan Stubbs':('IPL official Tristan Stubbs profile','https://www.iplt20.com/teams/royal-challengers-bengaluru/squad-details/20631','Page identifies Stubbs as a South African wicketkeeper batter and describes an anchor-finisher role. The URL team segment is inconsistent with the Delhi Capitals page content; no availability inferred.'),
 'Tim David':('RCB match review: Tim David, 6 April 2026','https://www.royalchallengers.com/rcb-cricket-news/news/putting-a-lot-of-pressure-on-the-opposition-was-super-fun-tim-david','RCB reports 70 not out from 25 balls against CSK and describes his flexible batting role. This single innings supports a role discussion, not statistical reliability or verified future availability.'),
 'Shashank Singh':('Punjab Kings official Shashank Singh profile','https://www.punjabkingsipl.in/players/63520-shashank-singh-profile','Official profile lists 2026 batting figures of 132 runs in 12 matches and a 2023 Vijay Hazare Trophy all-round performance. The biography has stale age wording; no current age copied from that text.'),
 'Namboori Tilak Varma':('Mumbai Indians Tilak Varma timeline','https://www.mumbaiindians.com/amp/news/timeline-the-rise-and-rise-of-our-starboy-tilak-varma','MI records his unbeaten 69 in the 2025 Asia Cup final and describes his June 2026 India A tri-series. These are separate public context, not source-model observations unless present in the RR pack.'),
 'Suryakumar Yadav':('Mumbai Indians official Suryakumar Yadav profile','https://www.mumbaiindians.com/players/11803-suryakumar-yadav-profile','Official profile reports 717 IPL runs in 2025 and describes his attacking batting range. This validates a role narrative, not the pressure classification used in the model.'),
 'Jos Buttler':('Gujarat Titans official Jos Buttler profile','https://www.gujarattitansipl.com/players/jos-buttler-9782-profile','Official profile describes his top-order career, 2022 Orange Cap and RR history. A historical connection to RR is not evidence that he is available for the 2027 auction.'),
 'Nicholas Pooran':('LSG official Nicholas Pooran profile','https://www.lucknowsupergiants.in/team/nicholas-pooran-63726-profile','LSG describes a left-handed power hitter with extensive T20 experience. Public career narrative remains separate from measured pressure reliability.'),
 'Washington Sundar':('Gujarat Titans official Washington Sundar profile','https://www.gujarattitansipl.com/players/washington-sundar-65859-profile','Official profile identifies a left-handed batter and off-spin all-rounder. Bowling utility does not contribute to his separate batting score; specialist batting opportunity should be checked.'),
 'Rasikh Salam':('RCB bowling coach on Rasikh Salam Dar, 13 May 2026','https://www.royalchallengers.com/rcb-cricket-news/news/a-keen-learner-of-the-game-omkar-salvi-on-rasikh-salam-dars-growth-through','RCB discusses his development during IPL 2026. Public spelling Rasikh Salam Dar maps to supplied name Rasikh Salam; his smaller pressure sample requires caution.'),
 'Jasprit Bumrah':('Mumbai Indians official Jasprit Bumrah profile','https://www.mumbaiindians.com/players/63755-jasprit-bumrah-profile','MI identifies a right-arm fast bowler and reports 18 wickets in 12 IPL 2025 games at economy 6.67. This official full-economy figure is external and is not substituted into the legal-ball off-bat model.'),
 'Mark Adair':('Cricket Ireland Northern Knights player profiles','https://cricketireland.ie/inter-provincial-series/northern-knights/','Cricket Ireland describes Adair as an opening and death bowler and an all-rounder. The narrative contains older relative dates, so it verifies role rather than current form or IPL readiness.'),
 'Mohammad Nawaz':('PCB official Mohammad Nawaz profile','https://www.pcb.com.pk/player/mohammad-nawaz-24046.html','PCB identifies a left-handed batter and left-arm orthodox bowler, born 21 March 1994. Strong T20I ranking does not establish IPL registration eligibility; no 2027 auction availability verified.'),
 'Trent Boult':('Mumbai Indians official Trent Boult profile','https://www.mumbaiindians.com/players/4338-trent-boult-profile','MI identifies a left-arm fast-medium bowler and reports 22 wickets in 16 IPL 2025 matches. His new-ball role should be distinguished from the model test against set batters.'),
 'Josh Hazlewood':('RCB Josh Hazlewood update, 1 September 2026','https://www.royalchallengers.com/rcb-cricket-news/news/the-best-way-forward-for-me-is-to-play-as-much-as-i-can-josh-hazlewood','RCB reports his comments on workload and physical condition in September 2026. This is a dated public update, not a medical clearance or guarantee of 2027 availability.'),
 'Rashid Khan':('Gujarat Titans official Rashid Khan profile','https://www.gujarattitansipl.com/players/rashid-khan-65748-profile','Official profile identifies his leg-spin and T20 all-round role. Batting ability is not counted in the separate bowling score; opposition and league translation remain scouting questions.'),
 'Wanindu Hasaranga':('IPL official Hasaranga replacement advisory, 10 April 2026','https://www.iplt20.com/news/article/lsg-sign-george-linde-as-a-replacement-for-wanindu-hasaranga','IPL confirms Hasaranga was ruled out of IPL 2026 with a hamstring injury and replaced at LSG. That dated injury report makes fitness and availability verification essential; it does not establish present injury status.'),
 'Khaleel Ahmed':('IPL official CSK-SRH trade advisory, 5 November 2026','https://www.iplt20.com/news/article/csk-and-srh-agree-to-four-player-trade','IPL confirms Khaleel moved to SRH ahead of IPL 2027. This is a confirmed trade, not evidence that he is an auction target. His historical dataset teams are displayed separately.'),
 'Prasidh Krishna':('Gujarat Titans official Prasidh Krishna profile','https://www.gujarattitansipl.com/players/prasidh-krishna-65702-profile','GT describes a right-arm fast-medium bowler and reports 25 wickets in 15 games in his 2025 Purple Cap season. Historical full-season statistics are separate from the scored RR subset.'),
}
GENERAL=[
 ('Official Rajasthan Royals 2026 auction review','https://www.rajasthanroyals.com/latest-news/ipl-2026-auction-rajasthan-royals-squad-full-players-list','Dated 16 December 2025. Records RR building its 2026 squad and buying Ravi Bishnoi and Adam Milne. These are not 2027 purse or vacancy figures.'),
 ('MCC Laws of Cricket','https://www.lords.org/mcc/about-the-laws-of-cricket','Authority for laws and legal-delivery distinctions. Source Overstep treated as a known no-ball; ambiguous other events are quarantined.'),
 ('PCB NOC list 2026','https://www.pcb.com.pk/press-release-detail/player-noc-list-2026-.html','Confirms Nawaz had listed NOCs for the 2026 T20 Blast and LPL. A non-IPL NOC does not confer IPL eligibility.'),
]

def main():
    path=ROOT/'output'/'analysis.json'
    d=json.loads(path.read_text(encoding='utf-8'))
    def entry(t): return dict(title=t[0],url=t[1],note=t[2],accessed=DATE)
    for kind in ['bat','bowl']:
        for p in d['rankings'][kind]:
            if p['name'] in RESEARCH:
                p['public_research']=[entry(RESEARCH[p['name']])]
            if p['name']=='Khaleel Ahmed':
                p['availability']='Confirmed trade to SRH before IPL 2027; not a verified auction candidate'
                p['risk']='IPL confirmed his transfer to SRH on 5 November 2026. Treat as a reliability benchmark, not an available RR auction target.'
            if p['name']=='Wanindu Hasaranga':
                p['risk']='IPL reported a hamstring injury and replacement for IPL 2026 on 10 April 2026. Verify present fitness separately. Full economy remains unavailable in the source model.'
            if p['name']=='Mohammad Nawaz':
                p['risk']='Evidence is T20I-based and does not establish IPL eligibility. Do not treat this statistical rank as an actionable IPL bid recommendation.'
            if p['name']=='Mahendra Singh Dhoni':
                p['risk']='Historical lower-order survival supports this descriptive score. His limited recent batting opportunities, age and unverified 2027 participation make this a benchmark rather than an assumed auction opportunity.'
            if p['name']=='Rasikh Salam':
                p['risk']='Only 138 high-pressure legal balls in the validated subset; interval is wide despite stable weight-scenario rank. Review full extras, recent workload and match film.'
    d['research']=[entry(t) for t in GENERAL]+[entry(v) for v in RESEARCH.values()]
    path.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'frontend'/'public'/'analysis.json').write_text(json.dumps(d,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    (ROOT/'output'/'public_research.json').write_text(json.dumps(d['research'],indent=2),encoding='utf-8')
    lines=['# Unstop submission entries','','Use this ordering in the two independent lists. Scores describe the supplied dataset, not confirmed IPL 2027 auction availability.','','| Rank | Batsman selection | BRS | Bowler selection | BoRS |','|---:|---|---:|---|---:|']
    for a,b in zip(d['rankings']['bat'][:10],d['rankings']['bowl'][:10]):
        lines.append(f"| {a['rank']} | {a['name']} | {a['score']:.2f} | {b['name']} | {b['score']:.2f} |")
    lines += ['', '## Form names', '', 'Names above exactly preserve the supplied roster display strings. The screenshots verify Mahendra Singh Dhoni as a selectable spelling. Other selected names have not been individually confirmed in the live dropdown.',
        '', '## Upload Your Report', '', 'Upload output/pdf/SupeRR_Selector_Report.pdf.', '', '## Dashboard Link', '',
        'Local-only delivery was selected. Leave this optional field blank. The dashboard runs at http://127.0.0.1:5173/ and is not accessible to external judges.', '',
        '## Share Your Journey', '', 'This field expects a URL to a reel, post or short video. It is optional. No post or video has been published on your behalf.', '',
        'Suggested caption or narration:', '',
        'We audited the RR data pack and found an extras field that contained category codes. We used only observable pre-ball context to define batting and bowling stress, compared players with contextual peers and their own non-high baseline, and tested sample sizes, intervals and alternative assumptions. The results identify scouting leads such as Rinku Singh and Rasikh Salam while keeping uncertainty visible. The rankings describe the supplied sample; future performance and auction availability require separate validation.', '',
        '45-second storyboard: 0-10s show the file audit; 10-20s explain pressure rules; 20-35s show a batter and bowler profile; 35-45s show intervals and the scouting shortlist.', '',
        '## Material limits', '', 'No complete scoreboard or economy can be recovered from missing extras. Batting holdout correlation is negative. Khaleel Ahmed has a verified SRH trade, and Nawaz has no verified IPL eligibility. These do not invalidate a data-only Round 1 ranking, but they constrain auction actions.']
    (ROOT/'output'/'Unstop_Submission.md').write_text('\n'.join(lines),encoding='utf-8')
    print(f"Added public research for {len(RESEARCH)} shortlisted players. Scores unchanged.")

if __name__=='__main__':main()
