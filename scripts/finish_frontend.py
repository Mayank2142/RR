from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=root/'frontend'/'src'/'App.tsx'
s=p.read_text(encoding='utf-8')
needle='<div className="profile-header">'
replacement='<a className="button button-outline profile-download" href={"/api/players/"+p.id+"/report?category="+p.category} download><Download size={14}/>Player PDF</a><div className="profile-header">'
if 'profile-download' not in s:
    assert s.count(needle)==1
    p.write_text(s.replace(needle,replacement),encoding='utf-8')
source=p.read_text(encoding='utf-8')
source=source.replace('<p>Dashboard link: <code>{data.dashboard_url??window.location.origin}</code></p>',
                      '<p>{data.dashboard_url?<>Dashboard link: <code>{data.dashboard_url}</code></>:<>The dashboard runs locally. Leave the optional dashboard-link field blank in Unstop.</>}</p>')
p.write_text(source,encoding='utf-8')
charts=root/'frontend'/'src'/'components'/'charts.tsx'
source=charts.read_text(encoding='utf-8')
for before,after in [('<Bar key={k}','<Bar isAnimationActive={false} key={k}'),
                     ('<Radar key={p.id}','<Radar isAnimationActive={false} key={p.id}'),
                     ('<Bar dataKey="rate"','<Bar isAnimationActive={false} dataKey="rate"'),
                     ('<Line type="monotone"','<Line isAnimationActive={false} type="monotone"'),
                     ('<Scatter data={points}','<Scatter isAnimationActive={false} data={points}')]:
    source=source.replace(before,after)
charts.write_text(source,encoding='utf-8')
