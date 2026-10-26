import shutil
import json, html, subprocess, os
from pages import PAGES
T=[float(x) for x in open('times.txt').read().split()]
seg=json.load(open('../full_segments.json')); tr=json.load(open('../full_translations.json'))
END=3570.3
os.makedirs('out/img',exist_ok=True)
def fmt(s): s=int(s); return f"{s//3600}:{s%3600//60:02d}:{s%60:02d}" if s>=3600 else f"{s//60}:{s%60:02d}"
starts=[T[p[0]-1] for p in PAGES]; ends=starts[1:]+[END]; starts[0]=0.0
cards=[]; toc=[]
for n,((idx,title,lines),a,b) in enumerate(zip(PAGES,starts,ends),1):
    img=f"img/p{n:02d}.jpg"
    subprocess.run(['ffmpeg','-loglevel','error','-y','-i',f's{idx:02d}.png','-vf','crop=1024:576:0:72','-q:v','4','out/'+img],check=True)
    shutil.copy(f'B/ja{n:02d}.jpg',f'out/img/j{n:02d}.jpg')
    body='';inl=False
    for l in lines:
        l=html.escape(l)
        if l.startswith('・'):
            if not inl: body+='<ul>'; inl=True
            body+=f'<li>{l[1:]}</li>'
        else:
            if inl: body+='</ul>'; inl=False
            body+=f'<p>{l}</p>'
    if inl: body+='</ul>'
    nar=''.join(f'<p><a href="#" data-t="{int(s["start"])}">{fmt(s["start"])}</a> {html.escape(tr[str(s["id"])])}</p>' for s in seg if a-0.01<=s['start']<b)
    cards.append(f'''<section id="p{n}" data-a="{a}" data-b="{b}"><h2><span class="n">{n}</span>{html.escape(title)}</h2>
<div class="tm"><a href="#" data-t="{int(a)}">▶ {fmt(a)}</a> 〜 {fmt(b)}</div>
<div class="row"><div class="col"><div class="lb">元の英語スライド</div><img loading="lazy" src="{img}"></div><div class="col"><div class="lb">日本語版スライド</div><img loading="lazy" src="img/j{n:02d}.jpg"></div></div>
<details><summary>この間の発言(日本語訳)</summary>{nar}</details></section>''')
    toc.append(f'<a href="#p{n}">{n}. {html.escape(title)}</a>')
page=f'''<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Marketo Fundamentals for AI 日本語スライド資料</title><style>
body{{font:15px/1.7 -apple-system,"Hiragino Sans",sans-serif;margin:0;background:#f4f4f6;color:#222}}
header{{padding:24px 20px;background:#1a1a2e;color:#fff}}header h1{{margin:0;font-size:22px}}header p{{margin:6px 0 0;opacity:.8;font-size:13px}}
main{{max-width:1100px;margin:auto;padding:16px}}nav{{background:#fff;border-radius:10px;padding:12px 16px;margin-bottom:16px;columns:2 320px;font-size:13px}}nav a{{display:block;color:#0a58ca;text-decoration:none;padding:1px 0}}
section{{background:#fff;border-radius:12px;padding:16px 18px;margin-bottom:18px;box-shadow:0 1px 3px #0001}}
h2{{margin:0 0 4px;font-size:18px}}.n{{display:inline-block;background:#d7263d;color:#fff;border-radius:6px;padding:0 8px;margin-right:8px;font-size:14px}}
.tm{{font-size:12px;color:#666;margin-bottom:10px}}.tm a,details a{{color:#0a58ca;text-decoration:none}}
.row{{display:flex;gap:16px;flex-wrap:wrap}}
.tx{{flex:1 1 320px}}.tx h3{{margin:0 0 6px;font-size:13px;color:#d7263d}}.tx p{{margin:4px 0}}.tx ul{{margin:4px 0;padding-left:20px}}.mu{{color:#999}}
details{{margin-top:12px;border-top:1px solid #eee;padding-top:8px}}summary{{cursor:pointer;font-weight:600;font-size:13px}}details p{{margin:6px 0;font-size:14px}}
#bar{{position:sticky;top:0;z-index:5;background:#f4f4f6;padding:8px 0;display:flex;gap:12px;flex-wrap:wrap;align-items:center}}#bar video{{width:360px;max-width:100%;background:#000;border-radius:8px}}#ctl{{font-size:13px;display:flex;flex-direction:column;gap:6px}}#go{{padding:6px 10px;cursor:pointer}}section{{scroll-margin-top:230px}}section.on{{outline:3px solid #d7263d}}
.row{{display:flex;gap:14px;flex-wrap:wrap}}.col{{flex:1 1 440px;min-width:0}}.lb{{font-size:12px;color:#888;margin-bottom:4px}}
.col img{{cursor:zoom-in;width:100%;display:block;border:1px solid #ddd;border-radius:4px;aspect-ratio:16/9;object-fit:cover}}
.jslide{{container-type:inline-size;position:relative;background:#fff;border:1px solid #ddd;border-left:10px solid #d7263d;border-radius:4px;aspect-ratio:16/9;box-sizing:border-box;}}.ji{{padding:3.5cqw 4cqw 6cqw;font-size:max(12px,2.3cqw);line-height:1.55}}
.ji h3{{margin:0 0 .6em;font-size:1.5em;line-height:1.3;color:#111}}.ji p{{margin:.25em 0}}.ji ul{{margin:.25em 0;padding-left:1.3em}}.ji li::marker{{color:#d7263d}}.ft{{position:absolute;left:4cqw;bottom:1.5cqw;color:#d7263d;font-weight:700;font-size:.8em}}
#v.big{{position:fixed;inset:2vh auto 2vh 2vw;width:calc(var(--vw,36)*1vw);height:96vh;max-width:none;z-index:100;object-fit:contain;box-shadow:0 0 0 100vmax rgba(0,0,0,.88)}}#vz.big{{position:fixed;top:10px;right:14px;z-index:101}}#sp{{position:fixed;left:calc(var(--vw,36)*1vw + 4vw);right:2vw;top:56px;bottom:2vh;z-index:99;display:none;flex-direction:column;align-items:center;justify-content:center;gap:8px;color:#ddd;font-size:13px}}#sp.on{{display:flex}}#sp input{{width:60%;max-width:320px}}#sp img{{max-width:100%;max-height:90%;object-fit:contain;box-shadow:0 0 30px #000}}#lb{{position:fixed;inset:0;background:rgba(0,0,0,.88);display:none;align-items:center;justify-content:center;z-index:99;cursor:zoom-out}}#lb.on{{display:flex}}#lb img{{max-width:96vw;max-height:96vh;object-fit:contain;box-shadow:0 0 30px #000}}
</style><header><h1>Marketo Fundamentals for AI(AI時代のMarketo基礎)— 日本語スライド資料</h1><p>MUGウェビナー 2026年5月 / スライドの日本語訳+発言の日本語訳。時刻をクリックすると動画の該当位置から再生します(動画 ../video と同じフォルダに video.mp4 を置いた場合)。※スライドの文字はOCRと目視をもとにした翻訳です。</p></header>
<main><div id="bar"><video id="v" src="video.mp4" controls preload="metadata"></video><div id="ctl"><div id="cur">再生位置のスライド: -</div><label><input type="checkbox" id="follow" checked> 再生に合わせて自動でスクロール</label><button id="go">いまのスライドへ移動</button><button id="vz">動画を拡大</button></div></div>
<nav>{''.join(toc)}</nav>{''.join(cards)}</main>
<div id="lb"><img alt=""></div><div id="sp"><img alt=""><div id="spc"></div><label>動画 <input type="range" id="spr" min="20" max="70" step="2"> スライド</label></div>
<script>const v=document.getElementById('v'),secs=[...document.querySelectorAll('section')],cur=document.getElementById('cur');let on=null;function spu(s){{if(!s)return;const i=s.querySelector('.col:last-child img');if(i)document.querySelector('#sp img').src=i.src;document.getElementById('spc').textContent=s.id.slice(1)+' / '+secs.length}}
function upd(){{const t=v.currentTime;const s=secs.find(x=>t>=+x.dataset.a&&t<+x.dataset.b)||secs[0];if(s!==on){{if(on)on.classList.remove('on');s.classList.add('on');on=s;cur.textContent='再生位置のスライド: '+s.id.slice(1)+' / '+secs.length;spu(s);if(document.getElementById('follow').checked)s.scrollIntoView({{behavior:'smooth',block:'start'}})}}}}
const RK='resume:'+location.pathname;let lastSave=0;function sv(){{try{{if(v.currentTime>2)localStorage.setItem(RK,String(v.currentTime))}}catch(e){{}}}}
v.addEventListener('timeupdate',()=>{{const n=Date.now();if(n-lastSave>2000){{lastSave=n;sv()}}}});v.addEventListener('pause',sv);addEventListener('pagehide',sv);
v.addEventListener('loadedmetadata',()=>{{let t=0;try{{t=+localStorage.getItem(RK)||0}}catch(e){{}}if(t>2&&t<v.duration-3){{v.currentTime=t;cur.textContent='前回の続き '+Math.floor(t/60)+':'+String(Math.floor(t%60)).padStart(2,'0')+' から(再生ボタンで再開)'}}}},{{once:true}});
v.addEventListener('timeupdate',upd);v.addEventListener('seeked',upd);document.getElementById('go').onclick=()=>{{upd();on&&on.scrollIntoView({{behavior:'smooth',block:'start'}})}};
const on_=()=>on;const lb=document.getElementById('lb');document.addEventListener('click',e=>{{if(e.target.closest('#lb')){{lb.classList.remove('on');return}}const im=e.target.closest('.col img');if(im){{lb.querySelector('img').src=im.src;lb.classList.add('on');return}}}});const vv=document.getElementById('v'),vz=document.getElementById('vz');const spr=document.getElementById('spr'),rs=document.documentElement.style;let w0=36;try{{w0=+localStorage.getItem('vw')||36}}catch(e){{}}rs.setProperty('--vw',w0);spr.value=w0;spr.oninput=()=>{{rs.setProperty('--vw',spr.value);try{{localStorage.setItem('vw',spr.value)}}catch(e){{}}}};function vbig(on){{vv.classList.toggle('big',on);document.getElementById('sp').classList.toggle('on',on);if(on){{upd();spu(on_())}}vz.classList.toggle('big',on);vz.textContent=on?'閉じる (Esc)':'動画を拡大'}}vz.onclick=()=>vbig(!vv.classList.contains('big'));vv.ondblclick=e=>{{e.preventDefault();vbig(!vv.classList.contains('big'))}};document.addEventListener('keydown',e=>{{if(e.key==='Escape'){{lb.classList.remove('on');vbig(false)}}}});
document.addEventListener('click',e=>{{const a=e.target.closest('a[data-t]');if(!a)return;e.preventDefault();const v=document.getElementById('v');v.currentTime=+a.dataset.t;v.play();}})</script></html>'''
open('out/index.html','w').write(page)
print(len(PAGES),'pages')
