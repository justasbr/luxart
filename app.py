"""Serve the local painting search without exposing the project or cache."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import argparse

ROOT=Path(__file__).resolve().parent
class Handler(SimpleHTTPRequestHandler):
    def translate_path(self,path):
        from urllib.parse import unquote, urlparse
        route=unquote(urlparse(path).path)
        if route=='/data/catalog.json':return str(ROOT/'data/catalog.json')
        allowed={'/':'index.html','/index.html':'index.html','/app.js':'app.js','/search.js':'search.js','/style.css':'style.css'}
        return str(ROOT/'web'/allowed.get(route,'__not_found__'))
    def end_headers(self):
        self.send_header('Cache-Control','no-store')
        super().end_headers()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--port',type=int,default=8765);args=p.parse_args()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    print(f'Painting search: http://127.0.0.1:{args.port}',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
