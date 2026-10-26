# 元画像(rawNN.png)と日本語版(jaNN.jpg)を見比べ、消えた「●」「■」等の行頭記号を検出する
import json,sys,numpy as np
from PIL import Image
O=json.load(open('ocr.json'))
def isolated(m,x,y,w,h):
    # 行頭記号は左右に余白がある(文字の一部ではない)
    r=m[max(0,y-2):y+h+2]
    g=lambda a,b: r[:,max(0,a):max(0,b)].any()
    return not g(x-8,x) and not g(x+w,x+w+8)
def blobs(m):
    H,W=m.shape; seen=np.zeros_like(m,bool); out=[]
    for y0,x0 in zip(*np.nonzero(m)):
        if seen[y0,x0]: continue
        st=[(y0,x0)]; seen[y0,x0]=True; ys=[];xs=[]
        while st and len(ys)<3000:
            y,x=st.pop(); ys.append(y); xs.append(x)
            for dy,dx in((1,0),(-1,0),(0,1),(0,-1)):
                a,b=y+dy,x+dx
                if 0<=a<H and 0<=b<W and m[a,b] and not seen[a,b]: seen[a,b]=True; st.append((a,b))
        h=max(ys)-min(ys)+1; w=max(xs)-min(xs)+1
        if 8<=w<=26 and 8<=h<=26 and 0.8<w/h<1.25 and len(ys)/(w*h)>0.7 and isolated(m,min(xs),min(ys),w,h): out.append((min(xs),min(ys),w,h))
    return out
FIX='--fix' in sys.argv
sys.argv=[a for a in sys.argv if a!='--fix']
pages=[int(a) for a in sys.argv[1:]] or sorted(int(k) for k in O)
for n in pages:
    raw=np.array(Image.open('raw%02d.png'%n).convert('L')); ja=np.array(Image.open('ja%02d.jpg'%n).convert('L'))
    lost=[]
    for b in O[str(n)]:
        x0=max(0,int(b['x'])-150); x1=int(b['x']+b['w']); y0=int(b['y'])-5; y1=int(b['y']+b['h'])+5
        reg=raw[y0:y1,x0:x1]<90
        for bx,by,w,h in blobs(reg):
            X,Y=x0+bx,y0+by
            if (ja[Y:Y+h,X:X+w]<90).mean()<0.3 and (raw[Y:Y+h,X:X+w]<90).mean()>0.6: lost.append((int(X),int(Y),int(w),int(h)))
    lost=[l for l in sorted(set(lost)) if l[1]>140]  # タイトル帯の字形は対象外
    if lost: print(n,lost)
    if FIX and lost:
        R=Image.open('raw%02d.png'%n).convert('RGB'); J=Image.open('ja%02d.jpg'%n).convert('RGB'); M=3
        for X,Y,w,h in lost:
            box=(X-M,Y-M,X+w+M,Y+h+M)
            if np.array(J.crop(box).convert('L')).mean()>200: J.paste(R.crop(box),box[:2])  # 周囲が明るい所だけ復元
        J.save('ja%02d.jpg'%n,quality=92)
