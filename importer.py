"""Resumable, rate-limited local catalogue import. Python standard library only."""
import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
import re
import urllib.error
import urllib.request
import urllib.robotparser
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from catalog import BASE, discover, parse_product
from rate import AdaptiveRate

ROOT=Path(__file__).resolve().parent
CACHE=ROOT/'data/cache'
OUT=ROOT/'data/catalog.json'
AGENT='PaveikslaiLocalCatalog/1.0'
WORKERS=32
limiter=AdaptiveRate()
robots=None

def sitemap_locations(xml):
    return [n.text.strip() for n in ET.fromstring(xml).iter() if n.tag.split('}')[-1]=='loc' and n.text]

def fetch(url, refresh=False):
    if not url.startswith(BASE+'/'): raise ValueError('Only luxart.com URLs are allowed')
    if robots and not robots.can_fetch(AGENT,url): raise RuntimeError('Disallowed by robots.txt: '+url)
    CACHE.mkdir(parents=True,exist_ok=True)
    path=CACHE/(hashlib.sha256(url.encode()).hexdigest()+'.html')
    if path.exists() and not refresh: return path.read_text()
    for attempt in range(3):
        epoch=limiter.acquire()
        try:
            req=urllib.request.Request(url,headers={'User-Agent':AGENT,'Accept-Language':'lt'})
            with urllib.request.urlopen(req,timeout=40) as r:
                body=r.read().decode('utf-8',errors='replace')
            if re.search(r'<title[^>]*>\s*(?:Just a moment|Access denied|Attention Required|Checking your browser)',body,re.I):
                limiter.failure(403)
                if attempt==2:
                    raise RuntimeError('Server returned a challenge/block page; not cached')
                continue
            limiter.success(epoch)
            path.write_text(body)
            return body
        except urllib.error.HTTPError as error:
            if error.code not in {403,408,429} and error.code < 500:
                raise
            limiter.failure(error.code,error.headers.get('Retry-After') if error.headers else None)
            if attempt==2: raise
        except (urllib.error.URLError,TimeoutError):
            limiter.failure(None)
            if attempt==2: raise

def collect_urls(refresh=False):
    urls=set(); seen=set(); queue=[BASE+'/sitemap_index.xml',BASE+'/wp-sitemap.xml']
    while queue:
        url=queue.pop(0)
        if url in seen: continue
        seen.add(url)
        try: locations=sitemap_locations(fetch(url,refresh))
        except Exception as e:
            print(f'Sitemap unavailable: {url}: {e}',flush=True); continue
        for loc in locations:
            if not loc.startswith(BASE+'/'): continue
            if loc.endswith('.xml') and ('product' in loc or 'sitemap_index' in loc): queue.append(loc)
            elif re.fullmatch(re.escape(BASE)+r'/paveikslai/[^/]+/',loc): urls.add(loc)
    if urls: return sorted(urls), 'sitemap'
    # Fall back to all catalogue pages, including intermediate pages absent from pagination links.
    first=fetch(BASE+'/paveikslai/',refresh)
    links=discover(first); urls.update(links['products'])
    last=max([1]+[int(re.search(r'/page/(\d+)/',p)[1]) for p in links['pages']])
    for page in range(2,last+1):
        links=discover(fetch(f'{BASE}/paveikslai/page/{page}/',refresh))
        if not links['products']: raise RuntimeError(f'No products on listing page {page}; refusing to mark import complete')
        urls.update(links['products'])
        print(f'Discovery page {page}/{last}: {len(urls)} works',flush=True)
    return sorted(urls),'listings'

def save(products, total, failures, complete, method):
    payload={'updated_at':datetime.now(timezone.utc).isoformat(),'complete':complete,'sample':False,
             'discovered':total,'failed':failures,'method':method,'products':sorted(products,key=lambda p:p['url'])}
    temp=OUT.with_suffix('.tmp');temp.write_text(json.dumps(payload,ensure_ascii=False));temp.replace(OUT)

def main():
    global robots, limiter
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--refresh',action='store_true',help='Fetch again instead of reusing cached HTML')
    ap.add_argument('--workers',type=int,default=WORKERS,help='Concurrent download workers (default: 32)')
    ap.add_argument('--start-rate',type=float,default=10,help='Initial shared requests/sec (default: 10)')
    ap.add_argument('--max-rate',type=float,default=40,help='Adaptive requests/sec ceiling (default: 40)')
    args=ap.parse_args()
    if args.workers < 1: ap.error('--workers must be positive')
    try: limiter=AdaptiveRate(args.start_rate,args.max_rate)
    except ValueError as error: ap.error(str(error))
    print(f'Starting import: {args.workers} workers; adaptive rate {limiter.rate:g} → {limiter.max_rate:g} req/sec. Reading robots.txt and discovering products…',flush=True)
    # Do not hide a failed robots request: network errors must stop before crawling.
    body=fetch(BASE+'/robots.txt',True)
    robots=urllib.robotparser.RobotFileParser();robots.parse(body.splitlines())
    urls,method=collect_urls(args.refresh)
    if not urls: raise RuntimeError('No products discovered. Site markup or access may have changed; existing catalogue kept.')
    print(f'Discovered {len(urls)} product URLs via {method}. Importing with {args.workers} workers. Cached pages are reused.',flush=True)
    products=[]; failures=[]
    def read(url):
        p=parse_product(fetch(url,args.refresh),url)
        if not p['title']: raise ValueError('Product title missing; page may be blocked')
        return p
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures={pool.submit(read,u):u for u in urls}
        for future in concurrent.futures.as_completed(futures):
            url=futures[future]
            try: products.append(future.result())
            except Exception as e: failures.append({'url':url,'error':str(e)})
            count=len(products)+len(failures)
            if count%20==0 or count==len(urls):
                save(products,len(urls),failures,count==len(urls) and not failures,method)
                print(f'{count}/{len(urls)} processed; {len(products)} works; {len(failures)} errors; target {limiter.rate:.2f} req/sec',flush=True)
    unknown=sum(not p['sizes'] for p in products)
    print(f'Saved {OUT}. {unknown} works have no parsed sizes (visible without dimension filters).')
    if failures: raise SystemExit('Partial import. Rerun to retry failed pages using the cache.')

if __name__=='__main__': main()
