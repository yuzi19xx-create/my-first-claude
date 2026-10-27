import os,re,sys,json
POS=os.path.join(os.path.abspath(sys.argv[1]),'..','pos.json')
def rd():
    try:return json.load(open(POS))
    except Exception:return {}
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
class H(SimpleHTTPRequestHandler):
    def do_POST(self):
        if not self.path.endswith('_pos'):return self.send_error(404)
        try:
            o=json.loads(self.rfile.read(int(self.headers.get('Content-Length',0))));d=rd()
            if o['k'] not in d or o['ts']>=d[o['k']]['ts']:d[o['k']]={'t':o['t'],'ts':o['ts']};json.dump(d,open(POS,'w'))
        except Exception:return self.send_error(400)
        self.send_response(204);self.end_headers()
    def send_head(self):
        if self.path.split('?')[0].endswith('_pos'):
            b=json.dumps(rd()).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(b)));self.end_headers();import io;self._left=None;return io.BytesIO(b)
        r=self.headers.get('Range');p=self.translate_path(self.path)
        if not r or not os.path.isfile(p): return super().send_head()
        m=re.match(r'bytes=(\d*)-(\d*)',r)
        n=os.path.getsize(p);a=int(m[1]) if m[1] else 0;b=int(m[2]) if m[2] else n-1;b=min(b,n-1)
        f=open(p,'rb');f.seek(a)
        self.send_response(206);self.send_header('Content-Type',self.guess_type(p));self.send_header('Content-Range',f'bytes {a}-{b}/{n}');self.send_header('Content-Length',str(b-a+1));self.send_header('Accept-Ranges','bytes');self.end_headers()
        self._left=b-a+1;return f
    def copyfile(self,s,d):
        left=getattr(self,'_left',None)
        if left is None: return super().copyfile(s,d)
        while left>0:
            c=s.read(min(65536,left))
            if not c:break
            try:d.write(c)
            except(BrokenPipeError,ConnectionResetError):break
            left-=len(c)
        self._left=None
    def end_headers(self):
        if 'Accept-Ranges' not in str(self._headers_buffer): self.send_header('Accept-Ranges','bytes')
        super().end_headers()
os.chdir(sys.argv[1]);ThreadingHTTPServer(('0.0.0.0',8000),H).serve_forever()
