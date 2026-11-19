import html,json
from pathlib import Path
p=Path('/home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime/lane_assoc_20261117')
d=json.loads((p/'result.json').read_text());lanes={'LEFT':120,'CURRENT':300,'RIGHT':480};colors={'LEFT':'#ffbe46','CURRENT':'#39ea84','RIGHT':'#45baff'}
svg=['<svg xmlns="http://www.w3.org/2000/svg" width="600" height="500" viewBox="0 0 600 500"><rect width="600" height="500" fill="#111c2b"/><text x="300" y="28" fill="#f3f6ff" text-anchor="middle" font-size="18">依据识别结果绘制的车道示意图</text>']
for x,name in ((120,'左侧车道'),(300,'自车车道'),(480,'右侧车道')):
 svg.append(f'<rect x="{x-80}" y="55" width="160" height="385" fill="#25384c" stroke="#6c8094" stroke-dasharray="7 7"/><text x="{x}" y="78" fill="#d6e4f2" text-anchor="middle" font-size="16">{name}</text>')
svg.append('<rect x="277" y="400" width="46" height="28" rx="7" fill="#d8e9ff"/><text x="300" y="420" fill="#132439" text-anchor="middle" font-size="14">自车</text>')
for t in d['targets']:
 side=t['lane_relation']
 if side not in lanes or t['delta_s_m'] is None:continue
 x=lanes[side];y=400-min(max(t['delta_s_m'],0),30)*12;col=colors[side]
 svg.append(f'<rect x="{x-44}" y="{y-24:.1f}" width="88" height="40" rx="7" fill="{col}"/><text x="{x}" y="{y-7:.1f}" text-anchor="middle" fill="#14202b" font-size="14">{html.escape(t["id"])}</text><text x="{x}" y="{y+10:.1f}" text-anchor="middle" fill="#14202b" font-size="12">{t["delta_s_m"]:.1f} m 前方</text>')
svg.append('<text x="300" y="475" fill="#aac0d9" text-anchor="middle" font-size="14">示意图：按车道分类排列，纵向距离来自传感器与地图</text></svg>')
(p/'lane_diagram.svg').write_text(''.join(svg),encoding='utf-8')
