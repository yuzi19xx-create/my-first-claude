import sys, json, subprocess, Vision, Quartz
from Foundation import NSURL
sys.path.insert(0,'.')
from pages import PAGES
def ocr(path):
    url=NSURL.fileURLWithPath_(path)
    src=Quartz.CGImageSourceCreateWithURL(url,None); img=Quartz.CGImageSourceCreateImageAtIndex(src,0,None)
    W=Quartz.CGImageGetWidth(img);H=Quartz.CGImageGetHeight(img)
    req=Vision.VNRecognizeTextRequest.alloc().init(); req.setRecognitionLevel_(0); req.setUsesLanguageCorrection_(True); req.setRecognitionLanguages_(['en-US'])
    h=Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(img,{}); h.performRequests_error_([req],None)
    out=[]
    for r in req.results():
        c=r.topCandidates_(1)[0]; b=r.boundingBox()
        out.append(dict(t=str(c.string()),conf=float(c.confidence()),x=b.origin.x*W,y=(1-b.origin.y-b.size.height)*H,w=b.size.width*W,h=b.size.height*H))
    return out,W,H
res={}
for n,(idx,title,lines) in enumerate(PAGES,1):
    raw=f'B/raw{n:02d}.png'
    subprocess.run(['ffmpeg','-loglevel','error','-y','-i',f's{idx:02d}.png','-vf','crop=1024:576:0:72,scale=2048:1152:flags=lanczos',raw],check=True)
    L,W,H=ocr(raw)
    L.sort(key=lambda d:(round(d['y']/6),d['x']))
    L=[d for d in L if d['h']>=17 and d['conf']>=0.3 and '©' not in d['t'] and d['t'].strip() not in ('Adobe','Confidential','Confidential.','Confidential') and any(ch.isalpha() for ch in d['t'])]
    blocks=[]
    for d in sorted(L,key=lambda d:d['y']):
        for b in blocks:
            last=b[-1]
            gap=d['y']-(last['y']+last['h'])
            left=abs(d['x']-last['x'])<30; cen=abs((d['x']+d['w']/2)-(last['x']+last['w']/2))<30
            if (left or cen) and -4<=gap<1.1*last['h'] and abs(d['h']-last['h'])<0.3*last['h']+4:
                b.append(d);break
        else: blocks.append([d])
    res[n]=[dict(id=f'{n}-{i}',lines=[x['t'] for x in b],x=min(x['x'] for x in b),y=min(x['y'] for x in b),w=max(x['x']+x['w'] for x in b)-min(x['x'] for x in b),h=max(x['y']+x['h'] for x in b)-min(x['y'] for x in b),lh=sum(x['h'] for x in b)/len(b),cen=not abs(b[0]['x']-b[-1]['x'])<30 if len(b)>1 else False) for i,b in enumerate(blocks)]
json.dump(res,open('B/ocr.json','w'),ensure_ascii=False)
tot=sum(len(v) for v in res.values());print(tot)
