"""Rebuild completed catalogue from cache and package a directly openable search page."""
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
from catalog import parse_product, Tree

ROOT=Path(__file__).resolve().parent

def rebuild(data,cache):
    if not data.get('complete'):
        raise ValueError('Wait for the import to finish before rebuilding the catalogue')
    products=[]; excluded=[]
    for old in data['products']:
        path=cache/(hashlib.sha256(old['url'].encode()).hexdigest()+'.html')
        html=path.read_text()
        product=parse_product(html,old['url'])
        # A sitemap can retain a draft URL that now resolves to a catalogue listing.
        if not any(n.has('summary') for n in Tree(html).root.all()):
            excluded.append({'url':old['url'],'reason':'Not an individual product page'})
            continue
        products.append(product)
    return {**data,'products':products,'excluded':excluded,'rebuilt_at':datetime.now(timezone.utc).isoformat()}

def bundle(data):
    html=(ROOT/'web/index.html').read_text()
    css=(ROOT/'web/style.css').read_text()
    search=(ROOT/'web/search.js').read_text().replace('export ','')
    app=(ROOT/'web/app.js').read_text()
    app='\n'.join(line for line in app.splitlines() if not line.startswith('import '))
    payload=json.dumps(data,ensure_ascii=False).replace('<','\\u003c')
    html=html.replace('<link rel="stylesheet" href="style.css">',f'<style>{css}</style>')
    html=html.replace('<script type="module" src="app.js"></script>',f'<script>globalThis.__CATALOG__={payload};</script><script type="module">{search}\n{app}</script>')
    html=html.replace('href="/"','href="?"')
    return html

if __name__=='__main__':
    path=ROOT/'data/catalog.json'
    data=rebuild(json.loads(path.read_text()),ROOT/'data/cache')
    temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(data,ensure_ascii=False));temporary.replace(path)
    out=ROOT/'dist/index.html';out.parent.mkdir(exist_ok=True);out.write_text(bundle(data))
    print(f'Packaged {len(data["products"])} products: {out}')
    print(f'Excluded {len(data["excluded"])} URLs that are not individual product pages.')
