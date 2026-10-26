import json, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from tr import TR
O = json.load(open('ocr.json'))
FP = '/System/Library/Fonts/ヒラギノ角ゴシック W%d.ttc'
_c = {}
def font(sz, wt):
    k = (sz, wt)
    if k not in _c: _c[k] = ImageFont.truetype(FP % wt, sz)
    return _c[k]
def wrap(d, text, f, maxw):
    out = []
    for para in text.split('\n'):
        cur = ''
        for ch in para:
            if d.textlength(cur + ch, font=f) > maxw and cur:
                out.append(cur); cur = ch
            else: cur += ch
        out.append(cur)
    return out
try:
    from man import MAN
except ImportError:
    MAN = {}
def man(n,img,d):
    m=MAN[n]
    for e in m['erase']: d.rectangle(e,fill=(255,255,255))
    for c,e in m.get('fill',[]): d.rectangle(e,fill=c)
    for x,cy,t,sz,wt,col,mw in m.get('lft',[]):
        f=font(sz,wt)
        while d.textlength(t,font=f)>mw and sz>16: sz-=1; f=font(sz,wt)
        d.text((x,cy-sz/2),t,font=f,fill=col)
    for cx,cy,t,sz,wt,col,mw in m.get('ctr',[]):
        f=font(sz,wt)
        while d.textlength(t,font=f)>mw and sz>16: sz-=1; f=font(sz,wt)
        d.text((cx-d.textlength(t,font=f)/2,cy-sz/2),t,font=f,fill=col)
    for x,y,mw,t,sz,wt,col,pitch in m['texts']:
        f=font(sz,wt); ls=wrap(d,t,f,mw)
        for i,l in enumerate(ls):
            d.text((x,y+i*(pitch or sz*1.2)-sz/2),l,font=f,fill=col)
def run(n):
    img = Image.open('raw%02d.png' % n).convert('RGB')
    a = np.asarray(img).astype(int)
    d = ImageDraw.Draw(img)
    H, W = a.shape[:2]
    if n in MAN: man(n,img,d)
    jobs = []
    for b in O[str(n)]:
        if b['id'] not in TR: continue
        x0, y0 = int(b['x']), int(b['y']); x1, y1 = int(x0 + b['w']), int(y0 + b['h'])
        p = 6
        X0, Y0, X1, Y1 = max(0, x0 - p), max(0, y0 - p), min(W, x1 + p), min(H, y1 + p)
        p = 3
        X0, Y0, X1, Y1 = max(0, x0 - p), max(0, y0 - p), min(W, x1 + p), min(H, y1 + p)
        sub = a[max(0,y0):y1, max(0,x0):x1].reshape(-1, 3)
        q = (sub // 16)
        key = q[:,0]*256 + q[:,1]*16 + q[:,2]
        vals, cnt = np.unique(key, return_counts=True)
        m = key == vals[cnt.argmax()]
        bg = np.median(sub[m], axis=0)
        reg = a[y0:y1, x0:x1].reshape(-1, 3)
        if len(reg) == 0: continue
        dist = np.abs(reg - bg).sum(1)
        # 枠線など別の色に引きずられないよう、背景と最もコントラストが出る輝度側(明背景なら暗い画素)で文字色を決める
        lum = reg.mean(1); far = dist >= np.percentile(dist, 70)
        top = reg[far & (lum <= np.percentile(lum[far], 30))] if bg.mean() > 128 else reg[far & (lum >= np.percentile(lum[far], 70))]
        if len(top) == 0: top = reg[dist >= np.percentile(dist, 92)]
        sat = top.max(1).astype(int) - top.min(1)
        if (sat > 80).mean() < 0.6 and (sat <= 80).any(): top = top[sat <= 80]  # 彩度の高い画素(赤枠等)が少数派なら文字色に使わない
        fg = tuple(int(v) for v in np.median(top, axis=0))
        if np.abs(np.array(fg) - bg).sum() < 120:
            fg = (0, 0, 0) if bg.mean() > 128 else (255, 255, 255)
        elif bg.mean() > 200 and max(fg) - min(fg) < 30:
            fg = (35, 35, 35)  # 薄い灰色の小文字は読みにくいので濃くする
        b['_ink'] = float((dist > 200).mean())
        if 'bgc' in b: bg = np.array(b['bgc'])
        if 'col' in b: fg = tuple(b['col'])
        jobs.append((b, (X0, Y0, X1, Y1), tuple(int(v) for v in bg), fg))
    for b, box, bg, fg in jobs:
        d.rectangle(box, fill=bg)
    for b, box, bg, fg in jobs:
        t = TR[b['id']]
        if not t: continue
        nl = max(1, len(b['lines']))
        lh = b['lh'] if b['lh'] else b['h'] / nl
        wt = 6 if lh > 44 else 4
        if b.get('_ink', 0) > 0.33: wt = 8   # 元が太字なら太字のまま
        if 'wt' in b: wt = b['wt']
        sz = max(14, int(lh * (0.95 if lh < 36 else 0.82)))
        bw = b['w'] * 1.08 + 12
        # allow more width if room on the right
        room = W - 20 - b['x']
        maxw = min(room, bw) if not b['cen'] else bw * 1.05
        cx0=b['x']+b['w']/2
        if b['cen']: maxw=min(maxw,2*min(cx0,W-cx0)-40)
        if 'mw' in b: maxw=b['mw']
        if 'sz' in b: sz=b['sz']
        hbudget = max(b['h'] * 1.15, lh * 1.3)
        while True:
            f = font(sz, wt)
            lines = wrap(d, t, f, maxw)
            step = int(sz * 1.25)
            if len(lines) * step <= hbudget + sz * 0.3 or sz <= 12: break
            sz -= 1
        if nl > 1 and len(lines) == nl and b['h'] / nl > step: step = int(b['h'] / nl)
        tot = len(lines) * step
        cy = b['y'] + b['h'] / 2
        y = cy - tot / 2
        cx = b['x'] + b['w'] / 2
        for ln in lines:
            w = d.textlength(ln, font=f)
            x = cx - w / 2 if b['cen'] else b['x']
            d.text((x, y), ln, font=f, fill=fg)
            y += step
    img.convert('RGB').save('ja%02d.jpg' % n, quality=90)
if __name__ == '__main__':
    for n in (map(int, sys.argv[1:]) or range(1, 50)): run(n)
